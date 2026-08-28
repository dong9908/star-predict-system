"""Create Astrometry.net WCS products with a local solver or the Nova web API."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import ExifTags, Image

from lib.io_utils import read_json, write_json
from lib.wsl import command_available as available_wsl_solver
from lib.wsl import windows_to_wsl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "wcs"
DEFAULT_NOVA_URL = "https://nova.astrometry.net"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def parse_args() -> argparse.Namespace:
    # An existing process environment takes precedence over the project .env file.
    load_dotenv(DEFAULT_ENV_FILE, override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Plate Solving할 원본 밤하늘 이미지")
    parser.add_argument("--backend", choices=("auto", "local", "nova"), default="auto")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ASTROMETRY_NET_API_KEY"),
        help="Nova API 키. 프로젝트 .env 또는 환경변수 사용 권장",
    )
    parser.add_argument("--nova-url", default=DEFAULT_NOVA_URL)
    parser.add_argument("--solve-field-command", default="solve-field")
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument(
        "--no-nova-fallback",
        action="store_true",
        help="auto 백엔드에서 로컬 solver 실패 시 Nova로 넘어가지 않음",
    )
    parser.add_argument("--force", action="store_true", help="기존 성공 WCS 캐시를 무시")
    parser.add_argument("--job-id", type=int, help="기존 Nova 작업 결과를 다시 내려받음")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--nova-request-retries", type=int, default=3)
    parser.add_argument("--downsample", type=float, default=2.0)
    parser.add_argument(
        "--scale-units",
        choices=("degwidth", "arcminwidth", "arcsecperpix"),
        default="degwidth",
    )
    parser.add_argument("--scale-lower", type=float)
    parser.add_argument("--scale-upper", type=float)
    parser.add_argument("--center-ra", type=float)
    parser.add_argument("--center-dec", type=float)
    parser.add_argument("--radius", type=float)
    parser.add_argument("--publicly-visible", action="store_true")
    parser.add_argument(
        "--allow-metadata-upload",
        action="store_true",
        help="EXIF/GPS가 포함될 수 있는 원본을 그대로 업로드(기본값은 메타데이터 제거)",
    )
    parser.add_argument("--allow-commercial-use", choices=("d", "y", "n"), default="n")
    parser.add_argument("--allow-modifications", choices=("d", "y", "n", "sa"), default="n")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.image.is_file():
        raise FileNotFoundError(f"입력 이미지를 찾을 수 없습니다: {args.image}")
    if args.timeout_seconds < 30:
        raise ValueError("timeout-seconds는 30 이상이어야 합니다.")
    if args.poll_interval < 1:
        raise ValueError("poll-interval은 1 이상이어야 합니다.")
    if args.nova_request_retries < 0:
        raise ValueError("nova-request-retries는 0 이상이어야 합니다.")
    if args.downsample < 1:
        raise ValueError("downsample은 1 이상이어야 합니다.")
    if (args.scale_lower is None) != (args.scale_upper is None):
        raise ValueError("--scale-lower와 --scale-upper는 함께 지정해야 합니다.")
    if args.scale_lower is not None and not 0 < args.scale_lower < args.scale_upper:
        raise ValueError("scale 범위를 확인해주세요.")
    center_values = (args.center_ra, args.center_dec, args.radius)
    if any(value is not None for value in center_values) and not all(
        value is not None for value in center_values
    ):
        raise ValueError("--center-ra, --center-dec, --radius는 함께 지정해야 합니다.")
    if args.center_ra is not None:
        if not 0 <= args.center_ra < 360 or not -90 <= args.center_dec <= 90 or args.radius <= 0:
            raise ValueError("중심 좌표 또는 탐색 반경을 확인해주세요.")


def output_paths(image: Path, output_root: Path) -> dict[str, Path]:
    folder = output_root / image.stem
    return {
        "folder": folder,
        "wcs": folder / f"{image.stem}.wcs",
        "new_fits": folder / f"{image.stem}.new",
        "corr": folder / f"{image.stem}.corr",
        "annotated": folder / f"{image.stem}_astrometry_annotated.jpg",
        "report": folder / f"{image.stem}_plate_solve.json",
        "stdout": folder / f"{image.stem}_solve_stdout.log",
        "stderr": folder / f"{image.stem}_solve_stderr.log",
    }


def scale_options(args: argparse.Namespace) -> list[str]:
    if args.scale_lower is None:
        return []
    return [
        "--scale-units",
        args.scale_units,
        "--scale-low",
        str(args.scale_lower),
        "--scale-high",
        str(args.scale_upper),
    ]


def center_options(args: argparse.Namespace) -> list[str]:
    if args.center_ra is None:
        return []
    return [
        "--ra",
        str(args.center_ra),
        "--dec",
        str(args.center_dec),
        "--radius",
        str(args.radius),
    ]


def solve_local(
    image: Path,
    paths: dict[str, Path],
    args: argparse.Namespace,
    executable: str,
    wsl_distribution: str | None = None,
) -> dict[str, Any]:
    def solver_path(path: Path) -> str:
        if not wsl_distribution:
            return str(path)
        return windows_to_wsl(path)

    solver_command = [executable]
    if wsl_distribution:
        solver_command = ["wsl.exe", "-d", wsl_distribution, "--", executable]
    command = [
        *solver_command,
        solver_path(image),
        "--dir",
        solver_path(paths["folder"]),
        "--out",
        image.stem,
        "--overwrite",
        "--no-plots",
        "--downsample",
        str(args.downsample),
        "--cpulimit",
        str(args.timeout_seconds),
        "--wcs",
        solver_path(paths["wcs"]),
        "--new-fits",
        solver_path(paths["new_fits"]),
        "--corr",
        solver_path(paths["corr"]),
        *scale_options(args),
        *center_options(args),
    ]
    print(f"로컬 solve-field를 실행합니다 ({'WSL ' + wsl_distribution if wsl_distribution else 'Windows'}).")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout_seconds + 30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError(f"로컬 Plate Solving이 {args.timeout_seconds + 30}초를 초과했습니다.") from error
    paths["stdout"].write_text(completed.stdout, encoding="utf-8")
    paths["stderr"].write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"solve-field 종료 코드 {completed.returncode}. 로그: {paths['stderr']}"
        )
    if not paths["wcs"].is_file():
        raise RuntimeError("solve-field는 종료됐지만 WCS 파일이 생성되지 않았습니다.")
    return {
        "backend": "wsl-local" if wsl_distribution else "local",
        "status": "success",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "command": command,
        "return_code": completed.returncode,
        "privacy": {
            "upload_copy_sanitized": None,
            "original_file_unchanged": True,
            "temporary_copy_deleted": None,
            "sensitive_values_recorded_in_report": False,
            "note": "로컬 Plate Solver만 사용하여 외부 서버에 이미지를 업로드하지 않았습니다.",
        },
    }


class NovaClient:
    def __init__(self, base_url: str, request_retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_retries = request_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Constellation-Plate-Solver/1.0",
                "Referer": f"{self.base_url}/api/login",
            }
        )

    def api_url(self, path: str) -> str:
        return f"{self.base_url}/api/{path.lstrip('/')}"

    def json_response(self, response: requests.Response) -> dict[str, Any]:
        response.raise_for_status()
        try:
            payload = response.json()
        except requests.JSONDecodeError as error:
            raise RuntimeError(f"Nova API가 JSON이 아닌 응답을 반환했습니다: {response.text[:300]}") from error
        if payload.get("status") == "error":
            raise RuntimeError(f"Nova API 오류: {payload.get('errormessage') or payload}")
        return payload

    def login(self, api_key: str) -> str:
        response = self.session.post(
            self.api_url("login"),
            data={"request-json": json.dumps({"apikey": api_key})},
            timeout=60,
        )
        payload = self.json_response(response)
        session_key = payload.get("session")
        if payload.get("status") != "success" or not session_key:
            raise RuntimeError(f"Nova 로그인에 실패했습니다: {payload.get('message') or payload}")
        return str(session_key)

    def upload(
        self,
        image: Path,
        request_payload: dict[str, Any],
        remote_filename: str | None = None,
    ) -> int:
        with image.open("rb") as file:
            response = self.session.post(
                self.api_url("upload"),
                files=(
                    ("request-json", (None, json.dumps(request_payload), "text/plain")),
                    ("file", (remote_filename or image.name, file, "application/octet-stream")),
                ),
                timeout=180,
            )
        payload = self.json_response(response)
        submission_id = payload.get("subid")
        if payload.get("status") != "success" or submission_id is None:
            raise RuntimeError(f"Nova 업로드에 실패했습니다: {payload}")
        return int(submission_id)

    def get_json(self, path: str) -> dict[str, Any]:
        for attempt in range(self.request_retries + 1):
            try:
                response = self.session.get(self.api_url(path), timeout=60)
                return self.json_response(response)
            except requests.RequestException:
                if attempt >= self.request_retries:
                    raise
                delay = min(2 ** attempt, 8)
                print(f"Nova API 연결 재시도 {attempt + 1}/{self.request_retries} ({delay}초 후)")
                time.sleep(delay)
        raise RuntimeError("Nova API 재시도 루프가 예기치 않게 종료됐습니다.")

    def wait_for_job(self, submission_id: int, timeout_seconds: int, poll_interval: float) -> int:
        deadline = time.monotonic() + timeout_seconds
        announced_jobs: set[int] = set()
        last_message_time = 0.0
        while time.monotonic() < deadline:
            submission = self.get_json(f"submissions/{submission_id}")
            jobs = [int(job) for job in submission.get("jobs", []) if job is not None]
            job_statuses: list[str | None] = []
            for job_id in jobs:
                if job_id not in announced_jobs:
                    print(f"Nova 작업 생성: job {job_id}")
                    announced_jobs.add(job_id)
                job = self.get_json(f"jobs/{job_id}")
                status = job.get("status")
                job_statuses.append(status)
                if status == "success":
                    return job_id
            if (
                jobs
                and submission.get("processing_finished")
                and job_statuses
                and all(status == "failure" for status in job_statuses)
            ):
                raise RuntimeError(f"Nova가 submission {submission_id}의 별 패턴을 해결하지 못했습니다.")
            now = time.monotonic()
            if now - last_message_time >= 20:
                print(f"Plate Solving 대기 중... submission {submission_id}")
                last_message_time = now
            time.sleep(min(poll_interval, max(0.1, deadline - time.monotonic())))
        raise TimeoutError(f"Nova Plate Solving이 {timeout_seconds}초 안에 완료되지 않았습니다.")

    def download(self, path: str, destination: Path) -> None:
        response = self.session.get(f"{self.base_url}/{path.lstrip('/')}", timeout=180)
        response.raise_for_status()
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.write_bytes(response.content)
        temporary.replace(destination)


def nova_request_payload(args: argparse.Namespace, session_key: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session": session_key,
        "allow_commercial_use": args.allow_commercial_use,
        "allow_modifications": args.allow_modifications,
        "publicly_visible": "y" if args.publicly_visible else "n",
        "downsample_factor": args.downsample,
        "tweak_order": 2,
        "crpix_center": True,
        "parity": 2,
    }
    if args.scale_lower is not None:
        payload.update(
            {
                "scale_type": "ul",
                "scale_units": args.scale_units,
                "scale_lower": args.scale_lower,
                "scale_upper": args.scale_upper,
            }
        )
    if args.center_ra is not None:
        payload.update(
            {
                "center_ra": args.center_ra,
                "center_dec": args.center_dec,
                "radius": args.radius,
            }
        )
    return payload


def safe_download(
    client: NovaClient,
    endpoint: str,
    destination: Path,
    warnings: list[str],
    required: bool = False,
) -> bool:
    try:
        client.download(endpoint, destination)
        return True
    except requests.RequestException as error:
        message = f"{endpoint} 다운로드 실패: {error}"
        warnings.append(message)
        if required:
            raise RuntimeError(message) from error
    return False


def metadata_summary(image_path: Path) -> dict[str, Any]:
    """Return presence flags only; never retain sensitive EXIF values."""
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()
            tag_ids = set(exif.keys())
            try:
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
            except (AttributeError, KeyError, TypeError):
                gps_ifd = {}
            return {
                "exif_tag_count": len(exif),
                "gps_metadata_detected": bool(gps_ifd or 34853 in tag_ids),
                "datetime_metadata_detected": bool(
                    tag_ids.intersection({306, 36867, 36868, 36880, 36881, 36882})
                ),
            }
    except (OSError, ValueError):
        return {
            "exif_tag_count": None,
            "gps_metadata_detected": None,
            "datetime_metadata_detected": None,
        }


def create_sanitized_upload_copy(source: Path, destination: Path) -> None:
    """Re-encode pixels without copying EXIF, XMP, GPS, or ICC metadata."""
    try:
        with Image.open(source) as image:
            image.convert("RGB").save(
                destination,
                format="JPEG",
                quality=95,
                subsampling=0,
                optimize=True,
            )
    except (OSError, ValueError) as error:
        raise RuntimeError(
            "개인정보 제거용 업로드 복사본을 만들 수 없습니다. 지원되는 이미지인지 "
            "확인하거나, 위험을 이해한 경우에만 --allow-metadata-upload를 사용하세요."
        ) from error

    sanitized = metadata_summary(destination)
    if sanitized["exif_tag_count"] != 0:
        destination.unlink(missing_ok=True)
        raise RuntimeError("업로드 복사본의 메타데이터 제거 검증에 실패했습니다.")


def solve_nova(
    image: Path,
    paths: dict[str, Path],
    args: argparse.Namespace,
) -> dict[str, Any]:
    client = NovaClient(args.nova_url, args.nova_request_retries)
    started = time.monotonic()
    submission_id: int | None = None
    privacy: dict[str, Any]
    if args.job_id is None:
        if not args.api_key:
            raise ValueError(
                f"Nova API 키가 없습니다. {DEFAULT_ENV_FILE}의 "
                "ASTROMETRY_NET_API_KEY 값을 입력해주세요."
            )
        original_metadata = metadata_summary(image)
        print(f"공개 설정: {'공개' if args.publicly_visible else '비공개'}")
        session_key = client.login(args.api_key)
        request_payload = nova_request_payload(args, session_key)
        if args.allow_metadata_upload:
            print("주의: 사용자가 허용하여 메타데이터가 포함될 수 있는 원본을 업로드합니다.")
            submission_id = client.upload(image, request_payload)
            privacy = {
                **original_metadata,
                "upload_copy_sanitized": False,
                "original_file_unchanged": True,
                "temporary_copy_deleted": None,
                "sensitive_values_recorded_in_report": False,
            }
        else:
            print("개인정보 보호: EXIF/GPS/촬영시간을 제거한 임시 복사본만 업로드합니다.")
            with tempfile.TemporaryDirectory(prefix="constellation_nova_") as temporary_dir:
                upload_copy = Path(temporary_dir) / f"{image.stem}_sanitized.jpg"
                create_sanitized_upload_copy(image, upload_copy)
                submission_id = client.upload(
                    upload_copy,
                    request_payload,
                    remote_filename=upload_copy.name,
                )
            privacy = {
                **original_metadata,
                "upload_copy_sanitized": True,
                "original_file_unchanged": True,
                "temporary_copy_deleted": True,
                "sensitive_values_recorded_in_report": False,
            }
        print(f"업로드 완료: submission {submission_id}")
        job_id = client.wait_for_job(submission_id, args.timeout_seconds, args.poll_interval)
    else:
        job_id = args.job_id
        privacy = {
            "upload_copy_sanitized": None,
            "original_file_unchanged": True,
            "temporary_copy_deleted": None,
            "sensitive_values_recorded_in_report": False,
            "note": "기존 작업 다운로드이므로 당시 업로드의 메타데이터 제거 여부를 알 수 없습니다.",
        }
        print(f"기존 Nova 작업 결과를 내려받습니다: job {job_id}")
        job_status = client.get_json(f"jobs/{job_id}")
        if job_status.get("status") != "success":
            raise RuntimeError(f"Nova job {job_id} 상태가 success가 아닙니다: {job_status}")

    info = client.get_json(f"jobs/{job_id}/info/")
    warnings: list[str] = []
    safe_download(client, f"wcs_file/{job_id}", paths["wcs"], warnings, required=True)
    safe_download(client, f"new_fits_file/{job_id}", paths["new_fits"], warnings)
    safe_download(client, f"corr_file/{job_id}", paths["corr"], warnings)
    safe_download(client, f"annotated_display/{job_id}", paths["annotated"], warnings)
    return {
        "backend": "nova",
        "status": "success",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "submission_id": submission_id,
        "job_id": job_id,
        "job_info_url": client.api_url(f"jobs/{job_id}/info/"),
        "publicly_visible": args.publicly_visible,
        "privacy": privacy,
        "calibration": info.get("calibration"),
        "objects_in_field": info.get("objects_in_field", []),
        "warnings": warnings,
    }


def available_local_executable(command: str) -> str | None:
    candidate = Path(command)
    if candidate.is_file():
        return str(candidate.resolve())
    return shutil.which(command)


def reusable_cache(image: Path, paths: dict[str, Path]) -> dict[str, Any] | None:
    if not paths["report"].is_file() or not paths["wcs"].is_file():
        return None
    try:
        report = read_json(paths["report"])
    except OSError:
        return None
    if not isinstance(report, dict):
        return None
    if report.get("status") != "success":
        return None
    try:
        if Path(report.get("image", "")).resolve() != image.resolve():
            return None
    except (OSError, TypeError):
        return None
    return report


def serializable_paths(paths: dict[str, Path]) -> dict[str, str]:
    return {
        name: str(path)
        for name, path in paths.items()
        if name not in {"folder", "report"} and path.is_file()
    }


def main() -> None:
    args = parse_args()
    args.image = args.image.resolve()
    validate_args(args)
    paths = output_paths(args.image, args.output_dir.resolve())
    paths["folder"].mkdir(parents=True, exist_ok=True)
    if not args.force:
        cached = reusable_cache(args.image, paths)
        if cached:
            print(f"기존 WCS 캐시 재사용: {paths['wcs']}")
            print(f"report: {paths['report']}")
            return
    local_executable = available_local_executable(args.solve_field_command)
    wsl_available = available_wsl_solver(args.wsl_distribution, args.solve_field_command)
    backend = args.backend
    if backend == "auto":
        backend = "local" if (local_executable or wsl_available) else "nova"

    report: dict[str, Any] = {
        "image": str(args.image),
        "requested_backend": args.backend,
        "selected_backend": backend,
        "status": "running",
        "parameters": {
            "downsample": args.downsample,
            "scale_units": args.scale_units if args.scale_lower is not None else None,
            "scale_lower": args.scale_lower,
            "scale_upper": args.scale_upper,
            "center_ra": args.center_ra,
            "center_dec": args.center_dec,
            "radius": args.radius,
            "timeout_seconds": args.timeout_seconds,
            "nova_request_retries": args.nova_request_retries,
            "wsl_distribution": args.wsl_distribution,
            "nova_fallback_enabled": args.backend == "auto" and not args.no_nova_fallback,
        },
    }
    try:
        if backend == "local":
            if not local_executable and not wsl_available:
                raise FileNotFoundError(
                    "solve-field를 찾을 수 없습니다. 로컬 Astrometry.net을 설치하거나 "
                    "--backend nova를 사용해주세요."
                )
            try:
                result = solve_local(
                    args.image,
                    paths,
                    args,
                    local_executable or args.solve_field_command,
                    None if local_executable else args.wsl_distribution,
                )
            except Exception as local_error:
                if args.backend != "auto" or args.no_nova_fallback:
                    raise
                print(f"로컬 Plate Solving 실패, Nova로 전환합니다: {local_error}")
                report["local_attempt"] = {
                    "status": "failed",
                    "error_type": type(local_error).__name__,
                    "error": str(local_error),
                    "backend": "wsl-local" if wsl_available and not local_executable else "local",
                }
                report["selected_backend"] = "nova"
                result = solve_nova(args.image, paths, args)
        else:
            result = solve_nova(args.image, paths, args)
        report.update(result)
        report["files"] = serializable_paths(paths)
        report["status"] = "success"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        write_json(paths["report"], report)
        print(f"Plate Solving 실패: {error}", file=sys.stderr)
        print(f"report: {paths['report']}", file=sys.stderr)
        raise SystemExit(1) from None

    write_json(paths["report"], report)
    print("Plate Solving 완료")
    if report.get("calibration"):
        calibration = report["calibration"]
        print(f"중심 RA/DEC: {calibration.get('ra')}, {calibration.get('dec')}")
        print(f"픽셀 스케일: {calibration.get('pixscale')} arcsec/pixel")
        print(f"방향: {calibration.get('orientation')} deg")
        print(f"반경: {calibration.get('radius')} deg")
    for name, path in paths.items():
        if name != "folder" and path.is_file():
            print(f"{name}: {path}")


if __name__ == "__main__":
    main()
