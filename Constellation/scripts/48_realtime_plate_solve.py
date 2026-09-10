"""Plate-solve one newly uploaded image and cache the result by SHA-256.

This stage is intentionally independent from the web server. Stage 49 can call
the same functions from the upload API after this command-line contract has
been verified. Local WSL Astrometry.net is used; the image is never uploaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits
from astropy.wcs import FITSFixedWarning, WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from PIL import Image, ImageOps

from lib.io_utils import configure_utf8_console, read_json, write_json
from lib.wsl import command_available


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "realtime_plate_solving"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, nargs="?", help="새로 업로드된 밤하늘 이미지")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--scale-lower", type=float, default=1.0)
    parser.add_argument("--scale-upper", type=float, default=180.0)
    parser.add_argument("--downsample", type=int, choices=(1, 2, 4, 8), help="자동 축소 배율 대신 사용할 값")
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--center-ra", type=float)
    parser.add_argument("--center-dec", type=float)
    parser.add_argument("--radius", type=float)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--two-stage-retry", action="store_true",
        help="1차 실패 시 상단 85%%/최대 1600px/downsample 2로 한 번 더 시도",
    )
    parser.add_argument("--second-stage-timeout-seconds", type=int, default=75)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check-environment", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.check_environment:
        return
    if args.image is None or not args.image.is_file():
        raise FileNotFoundError(f"입력 이미지를 찾을 수 없습니다: {args.image}")
    if args.image.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"지원하지 않는 이미지 확장자입니다: {args.image.suffix}")
    if args.timeout_seconds < 30:
        raise ValueError("--timeout-seconds는 30 이상이어야 합니다.")
    if args.second_stage_timeout_seconds < 30:
        raise ValueError("--second-stage-timeout-seconds는 30 이상이어야 합니다.")
    if not 0 < args.scale_lower < args.scale_upper:
        raise ValueError("화각 범위를 확인하세요.")
    hints = (args.center_ra, args.center_dec, args.radius)
    if any(value is not None for value in hints) and not all(value is not None for value in hints):
        raise ValueError("--center-ra, --center-dec, --radius는 함께 지정해야 합니다.")
    if args.center_ra is not None and (
        not 0 <= args.center_ra < 360 or not -90 <= args.center_dec <= 90 or args.radius <= 0
    ):
        raise ValueError("중심 좌표 또는 탐색 반경을 확인하세요.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def stage_image(source: Path, input_root: Path, image_hash: str) -> Path:
    target = input_root / f"{image_hash}{source.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return target
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    return target


def image_info(path: Path) -> dict[str, int]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return {"width": image.width, "height": image.height}


def wcs_summary(wcs_path: Path, width: int, height: int) -> dict[str, Any]:
    header = fits.getheader(wcs_path, 0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        celestial = WCS(header).celestial
    center = celestial.pixel_to_world((width - 1) / 2, (height - 1) / 2)
    footprint = celestial.calc_footprint(axes=(width, height))
    scales = proj_plane_pixel_scales(celestial) * 3600.0
    return {
        "center_ra": round(float(center.ra.deg), 8),
        "center_dec": round(float(center.dec.deg), 8),
        "pixel_scale_arcsec": round(float(sum(scales) / len(scales)), 6),
        "footprint_radec": [
            {"ra": round(float(ra), 8), "dec": round(float(dec), 8)}
            for ra, dec in footprint
        ],
    }


def prepare_second_stage(source: Path, target: Path) -> dict[str, Any]:
    """Create the Validation-selected sky85/max1600 retry input."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width, original_height = image.size
        crop_height = max(1, round(original_height * 0.85))
        image = image.crop((0, 0, original_width, crop_height))
        scale = min(1.0, 1600.0 / max(image.size))
        if scale < 1.0:
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        prepared_width, prepared_height = image.size
        # Use the actual independent X/Y ratios after integer rounding.
        scale_x = prepared_width / original_width
        scale_y = prepared_height / crop_height
        image.save(target, "JPEG", quality=95, subsampling=0)
    return {
        "crop_x": 0, "crop_y": 0,
        "crop_width": original_width, "crop_height": crop_height,
        "original_width": original_width, "original_height": original_height,
        "prepared_width": prepared_width, "prepared_height": prepared_height,
        "scale_x": scale_x, "scale_y": scale_y,
    }


def restore_original_wcs(source: Path, target: Path, transform: dict[str, Any]) -> None:
    """Map retry-image WCS pixels back onto the EXIF-normalized original image."""
    header = fits.getheader(source, 0)
    scale_x = float(transform["scale_x"])
    scale_y = float(transform["scale_y"])
    # FITS pixels are 1-based; preserve pixel-centre alignment while undoing resize/crop.
    header["CRPIX1"] = (float(header["CRPIX1"]) - 0.5) / scale_x + 0.5 + transform["crop_x"]
    header["CRPIX2"] = (float(header["CRPIX2"]) - 0.5) / scale_y + 0.5 + transform["crop_y"]
    if "CD1_1" in header:
        header["CD1_1"] = float(header["CD1_1"]) * scale_x
        header["CD2_1"] = float(header["CD2_1"]) * scale_x
        header["CD1_2"] = float(header["CD1_2"]) * scale_y
        header["CD2_2"] = float(header["CD2_2"]) * scale_y
    else:
        header["CDELT1"] = float(header["CDELT1"]) * scale_x
        header["CDELT2"] = float(header["CDELT2"]) * scale_y
    # SIP polynomials are expressed in pixels relative to CRPIX and must be
    # rescaled too; otherwise overlays drift away from stars near image edges.
    for prefix, output_scale in (("A", scale_x), ("AP", scale_x), ("B", scale_y), ("BP", scale_y)):
        marker = prefix + "_"
        for key in list(header):
            if not key.startswith(marker) or key == f"{prefix}_ORDER":
                continue
            parts = key[len(marker):].split("_")
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                i, j = (int(part) for part in parts)
                header[key] = float(header[key]) * (scale_x ** i) * (scale_y ** j) / output_scale
    # Astrometry .wcs files are header-only FITS (NAXIS=0); dimensions live here.
    header["IMAGEW"] = int(transform["original_width"])
    header["IMAGEH"] = int(transform["original_height"])
    header.add_history("Stage 54: restored WCS from sky85/max1600 retry image")
    target.parent.mkdir(parents=True, exist_ok=True)
    fits.PrimaryHDU(header=header).writeto(target, overwrite=True, output_verify="silentfix")


def environment_status(distribution: str) -> dict[str, Any]:
    available = command_available(distribution, "solve-field")
    return {
        "status": "ready" if available else "unavailable",
        "wsl_distribution": distribution,
        "solve_field_available": available,
        "message": (
            "WSL Astrometry.net Plate Solver를 사용할 수 있습니다."
            if available
            else "WSL Ubuntu에서 solve-field를 찾을 수 없습니다."
        ),
    }


def cached_result(path: Path, retry_failed: bool, force: bool) -> dict[str, Any] | None:
    if force or not path.is_file():
        return None
    result = read_json(path)
    if not isinstance(result, dict):
        return None
    if result.get("status") == "success":
        wcs_path = path.parent.parent / str(result.get("artifacts", {}).get("wcs", ""))
        return result if wcs_path.is_file() else None
    return None if retry_failed else result


def solve(args: argparse.Namespace) -> tuple[dict[str, Any], Path, bool]:
    source = args.image.resolve()
    output_root = args.output_dir.resolve()
    image_hash = sha256_file(source)
    result_dir = output_root / image_hash
    result_path = result_dir / "result.json"
    cached = cached_result(result_path, args.retry_failed, args.force)
    if cached is not None:
        return cached, result_path, True

    dimensions = image_info(source)
    staged = stage_image(source, output_root / "_inputs", image_hash)
    downsample = args.downsample or (
        4 if max(dimensions.values()) >= 3000 else (2 if max(dimensions.values()) >= 1200 else 1)
    )
    command = [
        sys.executable, str(PLATE_SOLVER), str(staged), "--backend", "local",
        "--no-nova-fallback", "--output-dir", str(output_root),
        "--wsl-distribution", args.wsl_distribution,
        "--timeout-seconds", str(args.timeout_seconds), "--downsample", str(downsample),
        "--scale-units", "degwidth", "--scale-lower", str(args.scale_lower),
        "--scale-upper", str(args.scale_upper),
    ]
    if args.center_ra is not None:
        command.extend([
            "--center-ra", str(args.center_ra), "--center-dec", str(args.center_dec),
            "--radius", str(args.radius),
        ])
    if args.force:
        command.append("--force")

    result_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    solver_report = result_dir / f"{image_hash}_plate_solve.json"
    wcs_path = result_dir / f"{image_hash}.wcs"
    low_level = read_json(solver_report, {})
    success = completed.returncode == 0 and wcs_path.is_file()
    attempts: list[dict[str, Any]] = [{
        "stage": 1, "profile": "broad",
        "status": "success" if success else "failed",
        "elapsed_seconds": elapsed,
        "downsample": downsample,
    }]
    second_stage: dict[str, Any] | None = None
    if not success and args.two_stage_retry:
        # Keep retry paths short: Windows Python may still enforce MAX_PATH.
        prepared = result_dir / "retry.jpg"
        transform = prepare_second_stage(source, prepared)
        retry_root = result_dir / "r"
        retry_command = [
            sys.executable, str(PLATE_SOLVER), str(prepared), "--backend", "local",
            "--no-nova-fallback", "--output-dir", str(retry_root),
            "--wsl-distribution", args.wsl_distribution,
            "--timeout-seconds", str(args.second_stage_timeout_seconds),
            "--downsample", "2", "--scale-units", "degwidth",
            "--scale-lower", "5", "--scale-upper", "160",
        ]
        if args.center_ra is not None:
            retry_command.extend([
                "--center-ra", str(args.center_ra), "--center-dec", str(args.center_dec),
                "--radius", str(args.radius),
            ])
        if args.force:
            retry_command.append("--force")
        # 07번은 입력 파일 stem을 결과 폴더명으로 사용한다.
        retry_dir = retry_root / prepared.stem
        retry_dir.mkdir(parents=True, exist_ok=True)
        retry_started = time.monotonic()
        retry_completed = subprocess.run(
            retry_command, cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        retry_elapsed = round(time.monotonic() - retry_started, 3)
        prepared_hash = sha256_file(prepared)
        retry_wcs = retry_dir / f"{prepared.stem}.wcs"
        retry_report = retry_dir / f"{prepared.stem}_plate_solve.json"
        retry_low_level = read_json(retry_report, {})
        retry_success = retry_completed.returncode == 0 and retry_wcs.is_file()
        attempts.append({
            "stage": 2, "profile": "sky85_downsample2",
            "status": "success" if retry_success else "failed",
            "elapsed_seconds": retry_elapsed, "downsample": 2,
        })
        second_stage = {
            "profile": "sky85_downsample2",
            "timeout_seconds": args.second_stage_timeout_seconds,
            "transform": transform,
            "prepared_sha256": prepared_hash,
        }
        if retry_success:
            restore_original_wcs(retry_wcs, wcs_path, transform)
            success = True
            low_level = retry_low_level
        else:
            low_level = retry_low_level
            completed = retry_completed
        elapsed = round(elapsed + retry_elapsed, 3)
    result: dict[str, Any] = {
        "schema_version": 1,
        "stage": 48,
        "status": "success" if success else "failed",
        "image_sha256": image_hash,
        "image": dimensions,
        "backend": "wsl-local-astrometry-net",
        "ai_used": False,
        "elapsed_seconds": elapsed,
        "solved_stage": attempts[-1]["stage"] if success else None,
        "attempts": attempts,
        "cached": False,
        "parameters": {
            "timeout_seconds": args.timeout_seconds,
            "downsample": downsample,
            "scale_units": "degwidth",
            "scale_lower": args.scale_lower,
            "scale_upper": args.scale_upper,
            "position_hint_used": args.center_ra is not None,
            "two_stage_retry": args.two_stage_retry,
        },
        "artifacts": {
            "wcs": str(wcs_path.relative_to(output_root)) if wcs_path.is_file() else "",
            "solver_report": (
                str(solver_report.relative_to(output_root)) if solver_report.is_file() else ""
            ),
        },
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if success:
        result["solution"] = wcs_summary(wcs_path, dimensions["width"], dimensions["height"])
    else:
        error_type = low_level.get("error_type") or "PlateSolveFailed"
        error = low_level.get("error") or completed.stderr.strip() or completed.stdout.strip()
        result["failure"] = {
            "error_type": str(error_type),
            "message": str(error)[-1500:] or "별 패턴을 해결하지 못했습니다.",
        }
    if second_stage is not None:
        result["second_stage"] = second_stage
    write_json(result_path, result)
    return result, result_path, False


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    if args.check_environment:
        status = environment_status(args.wsl_distribution)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        raise SystemExit(0 if status["status"] == "ready" else 1)

    result, result_path, was_cached = solve(args)
    result["cached"] = was_cached
    print("48번 실시간 Plate Solving " + ("성공" if result["status"] == "success" else "실패"))
    print(f"SHA-256: {result['image_sha256']}")
    print(f"캐시 사용: {'예' if was_cached else '아니요'}")
    print(f"result: {result_path}")
    raise SystemExit(0 if result["status"] == "success" else 2)


if __name__ == "__main__":
    main()
