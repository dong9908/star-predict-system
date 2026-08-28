"""Run stages 03 through 08 for one night-sky image."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {number: PROJECT_ROOT / "scripts" / f"{number:02d}_{name}.py" for number, name in (
    (3, "star_detection"),
    (4, "star_graph"),
    (5, "graph_matching"),
    (7, "plate_solving"),
    (8, "final_recognition"),
    (11, "wcs_constellation_overlay"),
)}
DETECTION_ROOT = PROJECT_ROOT / "data" / "results" / "star_detection"
GRAPH_ROOT = PROJECT_ROOT / "data" / "results" / "star_graph"
MATCHING_ROOT = PROJECT_ROOT / "data" / "results" / "graph_matching"
WCS_ROOT = PROJECT_ROOT / "data" / "wcs"
FINAL_ROOT = PROJECT_ROOT / "data" / "results" / "final_recognition"
OVERLAY_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "pipeline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="인식할 밤하늘 사진 한 장")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--sky-fraction", type=float, default=0.55)
    parser.add_argument("--max-stars", type=int, default=250)
    parser.add_argument("--minimum-usable-stars", type=int, default=7)
    parser.add_argument("--save-debug", action="store_true")
    parser.add_argument("--top-stars", type=int, default=100)
    parser.add_argument("--max-edge-factor", type=float, default=2.5)
    parser.add_argument("--ratio-tolerance", type=float, default=0.035)
    parser.add_argument("--max-observed-triangles", type=int, default=200)
    parser.add_argument("--max-hypotheses", type=int, default=120)
    parser.add_argument("--match-radius-factor", type=float, default=0.12)
    parser.add_argument("--plate-backend", choices=("auto", "local", "nova"), default="auto")
    parser.add_argument(
        "--skip-plate-solving",
        action="store_true",
        help="07단계를 실행하지 않음. 기존 WCS가 있으면 08단계에서 재사용",
    )
    parser.add_argument("--plate-timeout-seconds", type=int, default=900)
    parser.add_argument("--plate-downsample", type=float, default=4.0)
    parser.add_argument("--nova-request-retries", type=int, default=3)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--no-nova-fallback", action="store_true")
    parser.add_argument("--scale-units", choices=("degwidth", "arcminwidth", "arcsecperpix"), default="degwidth")
    parser.add_argument("--scale-lower", type=float, default=40.0)
    parser.add_argument("--scale-upper", type=float, default=110.0)
    parser.add_argument("--center-ra", type=float)
    parser.add_argument("--center-dec", type=float)
    parser.add_argument("--radius", type=float)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--captured-at")
    parser.add_argument("--utc-offset-hours", type=float)
    parser.add_argument("--gaia-max-magnitude", type=float, default=8.0)
    parser.add_argument("--global-match-radius-px", type=float, default=5.0)
    parser.add_argument("--minimum-global-matches", type=int, default=12)
    parser.add_argument("--max-candidate-reprojection-error-px", type=float, default=5.0)
    parser.add_argument("--skip-wcs-overlay", action="store_true")
    parser.add_argument("--include-two-star-constellations", action="store_true")
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="03~05단계를 기존 결과와 관계없이 다시 실행",
    )
    parser.add_argument(
        "--force-plate-solving",
        action="store_true",
        help="기존 WCS가 있어도 07단계를 다시 실행(외부 업로드가 다시 발생할 수 있음)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def same_source(path: Path, image: Path) -> bool:
    if not path.is_file():
        return False
    try:
        payload = load_json(path)
        return Path(str(payload.get("image", ""))).resolve() == image.resolve()
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_stage(
    number: int,
    command: list[str],
    log_path: Path,
    verbose: bool,
) -> dict[str, Any]:
    print(f"[{number:02d}] 실행 중...")
    started_at = utc_now()
    started = time.monotonic()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    output = "\n".join(part.rstrip() for part in (completed.stdout, completed.stderr) if part)
    log_path.write_text(output + ("\n" if output else ""), encoding="utf-8")
    elapsed = round(time.monotonic() - started, 3)
    if verbose and output:
        print(output)
    status = "success" if completed.returncode == 0 else "failed"
    print(f"[{number:02d}] {status} ({elapsed:.2f}초)")
    return {
        "stage": number,
        "status": status,
        "started_at_utc": started_at,
        "elapsed_seconds": elapsed,
        "return_code": completed.returncode,
        "command": command,
        "log": str(log_path),
        "error_tail": None if completed.returncode == 0 else output[-1000:],
    }


def reused_stage(number: int, artifact: Path) -> dict[str, Any]:
    print(f"[{number:02d}] 기존 결과 재사용: {artifact}")
    return {
        "stage": number,
        "status": "reused",
        "artifact": str(artifact),
        "elapsed_seconds": 0.0,
    }


def skipped_stage(number: int, reason: str) -> dict[str, Any]:
    print(f"[{number:02d}] 건너뜀: {reason}")
    return {"stage": number, "status": "skipped", "reason": reason, "elapsed_seconds": 0.0}


def append_optional_pair(command: list[str], option_a: str, value_a: Any, option_b: str, value_b: Any) -> None:
    if value_a is not None and value_b is not None:
        command.extend((option_a, str(value_a), option_b, str(value_b)))


def write_pipeline_report(
    report_path: Path,
    text_path: Path,
    report: dict[str, Any],
) -> None:
    report["finished_at_utc"] = utc_now()
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    outcome = report["outcome"]
    lines = [
        "별자리 단일 사진 파이프라인 결과",
        f"이미지: {report['image']}",
        f"상태: {outcome['status']}",
        f"후보: {outcome.get('candidate') or '없음'}",
        f"실패 코드: {outcome.get('failure_code') or '없음'}",
        f"설명: {outcome.get('reason') or ''}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    image = args.image.resolve()
    if not image.is_file():
        raise FileNotFoundError(f"입력 이미지를 찾을 수 없습니다: {image}")
    if args.force_plate_solving and args.skip_plate_solving:
        raise ValueError("--force-plate-solving과 --skip-plate-solving은 함께 사용할 수 없습니다.")
    if (args.scale_lower is None) != (args.scale_upper is None):
        raise ValueError("--scale-lower와 --scale-upper는 함께 지정해야 합니다.")
    if (args.latitude is None) != (args.longitude is None):
        raise ValueError("--latitude와 --longitude는 함께 지정해야 합니다.")
    stem = image.stem
    pipeline_dir = args.output_dir.resolve() / stem
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    report_path = pipeline_dir / f"{stem}_pipeline.json"
    text_path = pipeline_dir / f"{stem}_pipeline.txt"
    report: dict[str, Any] = {
        "image": str(image),
        "started_at_utc": utc_now(),
        "parameters": vars(args) | {"image": str(image), "output_dir": str(args.output_dir.resolve())},
        "stages": [],
        "outcome": {"status": "running", "candidate": None, "failure_code": None, "reason": None},
    }
    # argparse Path values must be converted before JSON serialization.
    report["parameters"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in report["parameters"].items()
    }

    detection = DETECTION_ROOT / stem / f"{stem}_stars.json"
    graph = GRAPH_ROOT / stem / f"{stem}_graph.json"
    matching = MATCHING_ROOT / stem / f"{stem}_matching.json"
    plate_report = WCS_ROOT / stem / f"{stem}_plate_solve.json"
    wcs_new = WCS_ROOT / stem / f"{stem}.new"
    wcs_header = WCS_ROOT / stem / f"{stem}.wcs"
    final_json = FINAL_ROOT / stem / f"{stem}_final.json"
    overlay_json = OVERLAY_ROOT / stem / f"{stem}_wcs_constellations.json"
    validation_json = PROJECT_ROOT / "data" / "results" / "match_validation" / stem / f"{stem}_validation.json"

    if not args.force_local and same_source(detection, image):
        report["stages"].append(reused_stage(3, detection))
    else:
        command = [
            sys.executable,
            str(SCRIPTS[3]),
            str(image),
            "--sky-fraction",
            str(args.sky_fraction),
            "--max-stars",
            str(args.max_stars),
            "--minimum-usable-stars",
            str(args.minimum_usable_stars),
        ]
        if args.save_debug:
            command.append("--save-debug")
        stage = run_stage(3, command, pipeline_dir / "03_star_detection.log", args.verbose)
        report["stages"].append(stage)
        if stage["status"] == "failed":
            report["outcome"] = {
                "status": "failed",
                "candidate": None,
                "failure_code": "pipeline_error",
                "reason": "03단계 별 검출 실행에 실패했습니다.",
            }
            write_pipeline_report(report_path, text_path, report)
            raise SystemExit(1)

    detection_payload = load_json(detection)
    if not detection_payload.get("usable_for_graph", False):
        detected = int(detection_payload.get("detected_stars", 0))
        minimum = int(detection_payload.get("minimum_usable_stars", args.minimum_usable_stars))
        for number in (4, 5, 7, 8):
            report["stages"].append(skipped_stage(number, "그래프 생성에 필요한 별이 부족함"))
        report["outcome"] = {
            "status": "failed",
            "candidate": None,
            "failure_code": "too_few_stars",
            "reason": f"별 후보가 {detected}개로 최소 기준 {minimum}개보다 적습니다.",
        }
        write_pipeline_report(report_path, text_path, report)
        print(report["outcome"]["reason"])
        print(f"pipeline_json: {report_path}")
        print(f"pipeline_text: {text_path}")
        return

    if not args.force_local and same_source(graph, image):
        report["stages"].append(reused_stage(4, graph))
    else:
        command = [
            sys.executable,
            str(SCRIPTS[4]),
            str(detection),
            "--top-stars",
            str(args.top_stars),
            "--max-edge-factor",
            str(args.max_edge_factor),
        ]
        stage = run_stage(4, command, pipeline_dir / "04_star_graph.log", args.verbose)
        report["stages"].append(stage)
        if stage["status"] == "failed":
            report["outcome"] = {
                "status": "failed",
                "candidate": None,
                "failure_code": "pipeline_error",
                "reason": "04단계 별 그래프 생성에 실패했습니다.",
            }
            write_pipeline_report(report_path, text_path, report)
            raise SystemExit(1)

    if not args.force_local and same_source(matching, image):
        report["stages"].append(reused_stage(5, matching))
    else:
        command = [
            sys.executable,
            str(SCRIPTS[5]),
            str(graph),
            "--ratio-tolerance",
            str(args.ratio_tolerance),
            "--max-observed-triangles",
            str(args.max_observed_triangles),
            "--max-hypotheses",
            str(args.max_hypotheses),
            "--match-radius-factor",
            str(args.match_radius_factor),
        ]
        stage = run_stage(5, command, pipeline_dir / "05_graph_matching.log", args.verbose)
        report["stages"].append(stage)
        if stage["status"] == "failed":
            report["outcome"] = {
                "status": "failed",
                "candidate": None,
                "failure_code": "no_candidate",
                "reason": "05단계에서 별자리 후보를 만들지 못했습니다.",
            }
            write_pipeline_report(report_path, text_path, report)
            raise SystemExit(1)

    has_reusable_wcs = (
        same_source(plate_report, image)
        and load_json(plate_report).get("status") == "success"
        and (wcs_new.is_file() or wcs_header.is_file())
    )
    if args.skip_plate_solving:
        reason = "사용자 옵션으로 Plate Solving을 실행하지 않음"
        if has_reusable_wcs:
            reason += "; 기존 WCS는 08단계에서 사용"
        report["stages"].append(skipped_stage(7, reason))
    elif has_reusable_wcs and not args.force_plate_solving:
        report["stages"].append(reused_stage(7, wcs_new if wcs_new.is_file() else wcs_header))
    else:
        command = [
            sys.executable,
            str(SCRIPTS[7]),
            str(image),
            "--backend",
            args.plate_backend,
            "--timeout-seconds",
            str(args.plate_timeout_seconds),
            "--nova-request-retries",
            str(args.nova_request_retries),
            "--downsample",
            str(args.plate_downsample),
            "--wsl-distribution",
            args.wsl_distribution,
        ]
        if args.no_nova_fallback:
            command.append("--no-nova-fallback")
        if args.force_plate_solving:
            command.append("--force")
        if args.scale_lower is not None or args.scale_upper is not None:
            append_optional_pair(command, "--scale-lower", args.scale_lower, "--scale-upper", args.scale_upper)
            command.extend(("--scale-units", args.scale_units))
        if any(value is not None for value in (args.center_ra, args.center_dec, args.radius)):
            if not all(value is not None for value in (args.center_ra, args.center_dec, args.radius)):
                raise ValueError("--center-ra, --center-dec, --radius는 함께 지정해야 합니다.")
            command.extend(
                ("--center-ra", str(args.center_ra), "--center-dec", str(args.center_dec), "--radius", str(args.radius))
            )
        stage = run_stage(7, command, pipeline_dir / "07_plate_solving.log", args.verbose)
        report["stages"].append(stage)
        # Continue to 08 even on failure so it can emit plate_solve_failed.

    command = [
        sys.executable,
        str(SCRIPTS[8]),
        str(matching),
        "--gaia-max-magnitude",
        str(args.gaia_max_magnitude),
        "--global-match-radius-px",
        str(args.global_match_radius_px),
        "--minimum-global-matches",
        str(args.minimum_global_matches),
        "--max-candidate-reprojection-error-px",
        str(args.max_candidate_reprojection_error_px),
    ]
    for option, value in (
        ("--latitude", args.latitude),
        ("--longitude", args.longitude),
        ("--captured-at", args.captured_at),
        ("--utc-offset-hours", args.utc_offset_hours),
    ):
        if value is not None:
            command.extend((option, str(value)))
    print("[06] 검증은 08단계 내부에서 실행됩니다.")
    stage = run_stage(8, command, pipeline_dir / "08_final_recognition.log", args.verbose)
    report["stages"].append(
        {
            "stage": 6,
            "status": "success" if stage["status"] == "success" and validation_json.is_file() else "failed",
            "execution": "08단계 내부 실행",
            "artifact": str(validation_json) if validation_json.is_file() else None,
            "elapsed_seconds": None,
        }
    )
    report["stages"].append(stage)
    if stage["status"] == "failed" or not final_json.is_file():
        report["outcome"] = {
            "status": "failed",
            "candidate": None,
            "failure_code": "pipeline_error",
            "reason": "08단계 최종 판정 생성에 실패했습니다.",
        }
        write_pipeline_report(report_path, text_path, report)
        raise SystemExit(1)

    final = load_json(final_json)
    candidate = final.get("candidate") or {}
    failure = final.get("failure_assessment") or {}
    graph_outcome = {
        "status": final.get("decision", {}).get("status"),
        "candidate": candidate.get("iau"),
        "candidate_name": candidate.get("native_name"),
        "confirmed": bool(final.get("decision", {}).get("confirmed")),
        "failure_code": failure.get("primary_code"),
        "failure_codes": failure.get("codes", []),
        "reason": final.get("decision", {}).get("reason"),
        "final_json": str(final_json),
        "final_image": str(FINAL_ROOT / stem / f"{stem}_final.jpg"),
    }
    report["graph_outcome"] = graph_outcome

    plate_is_current_success = (
        same_source(plate_report, image)
        and load_json(plate_report).get("status") == "success"
        and (wcs_new.is_file() or wcs_header.is_file())
    )
    overlay: dict[str, Any] | None = None
    if args.skip_wcs_overlay:
        report["stages"].append(skipped_stage(11, "사용자 옵션으로 WCS 별자리 오버레이를 실행하지 않음"))
    elif not plate_is_current_success:
        report["stages"].append(skipped_stage(11, "사용 가능한 현재 사진의 WCS가 없음"))
    else:
        command = [sys.executable, str(SCRIPTS[11]), str(image)]
        if args.include_two_star_constellations:
            command.append("--include-two-star")
        overlay_stage = run_stage(11, command, pipeline_dir / "11_wcs_constellation_overlay.log", args.verbose)
        report["stages"].append(overlay_stage)
        if overlay_stage["status"] == "success" and overlay_json.is_file():
            overlay = load_json(overlay_json)

    if overlay and overlay.get("decision", {}).get("status") == "recognized":
        recognized = overlay["decision"].get("constellations", [])
        report["outcome"] = {
            "status": "recognized",
            "candidate": recognized[0] if recognized else None,
            "constellations": recognized,
            "confirmed": True,
            "recognition_method": "wcs_stellarium_projection",
            "failure_code": None,
            "failure_codes": [],
            "reason": overlay["decision"].get("reason"),
            "overlay_json": str(overlay_json),
            "overlay_image": str(OVERLAY_ROOT / stem / f"{stem}_wcs_overlay.jpg"),
            "graph_final_json": str(final_json),
        }
    else:
        report["outcome"] = graph_outcome
    write_pipeline_report(report_path, text_path, report)
    print("파이프라인 완료")
    if report["outcome"].get("constellations"):
        print(f"인식된 별자리: {', '.join(report['outcome']['constellations'])}")
    else:
        print(f"최종 후보: {report['outcome'].get('candidate') or '없음'}")
    print(f"최종 상태: {report['outcome']['status']}")
    print(f"실패 코드: {report['outcome'].get('failure_code') or '없음'}")
    print(f"pipeline_json: {report_path}")
    print(f"pipeline_text: {text_path}")
    if report["outcome"].get("final_json"):
        print(f"final_json: {report['outcome']['final_json']}")
    elif report["outcome"].get("graph_final_json"):
        print(f"graph_final_json: {report['outcome']['graph_final_json']}")
    if report["outcome"].get("final_image"):
        print(f"final_image: {report['outcome']['final_image']}")
    if report["outcome"].get("overlay_image"):
        print(f"overlay_image: {report['outcome']['overlay_image']}")


if __name__ == "__main__":
    main()
