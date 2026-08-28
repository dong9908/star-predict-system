"""Run final validation and package the constellation recognition result."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SCRIPT = PROJECT_ROOT / "scripts" / "06_match_validation.py"
DEFAULT_WCS_ROOT = PROJECT_ROOT / "data" / "wcs"
DEFAULT_VALIDATION_ROOT = PROJECT_ROOT / "data" / "results" / "match_validation"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "final_recognition"
DEFAULT_DETECTION_ROOT = PROJECT_ROOT / "data" / "results" / "star_detection"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matching", type=Path, help="05단계의 *_matching.json")
    parser.add_argument("--wcs", type=Path, help="07단계의 .new, .wcs 또는 FITS 파일")
    parser.add_argument("--wcs-root", type=Path, default=DEFAULT_WCS_ROOT)
    parser.add_argument("--validation-output-dir", type=Path, default=DEFAULT_VALIDATION_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--captured-at", help="ISO 8601 촬영 시각")
    parser.add_argument("--utc-offset-hours", type=float)
    parser.add_argument("--minimum-altitude-deg", type=float, default=-5.0)
    parser.add_argument("--max-angular-error-arcsec", type=float, default=180.0)
    parser.add_argument("--gaia-max-magnitude", type=float, default=8.0)
    parser.add_argument("--global-match-radius-px", type=float, default=5.0)
    parser.add_argument("--minimum-global-matches", type=int, default=12)
    parser.add_argument("--max-candidate-reprojection-error-px", type=float, default=5.0)
    return parser.parse_args()


def stem_from_matching(path: Path) -> str:
    stem = path.stem
    return stem[:-9] if stem.endswith("_matching") else stem


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_wcs(stem: str, explicit: Path | None, root: Path) -> Path | None:
    if explicit is not None:
        result = explicit.resolve()
        if not result.is_file():
            raise FileNotFoundError(f"WCS 파일을 찾을 수 없습니다: {result}")
        return result
    folder = root.resolve() / stem
    plate_report = folder / f"{stem}_plate_solve.json"
    if plate_report.is_file():
        try:
            if load_json(plate_report).get("status") == "failed":
                return None
        except (OSError, ValueError, json.JSONDecodeError):
            return None
    # .new contains the image dimensions, so Astropy's header-only .wcs warning is avoided.
    for candidate in (folder / f"{stem}.new", folder / f"{stem}.wcs"):
        if candidate.is_file():
            return candidate
    return None


def run_validation(args: argparse.Namespace, matching: Path, wcs: Path | None) -> Path:
    command = [
        sys.executable,
        str(VALIDATION_SCRIPT),
        str(matching),
        "--output-dir",
        str(args.validation_output_dir.resolve()),
        "--minimum-altitude-deg",
        str(args.minimum_altitude_deg),
        "--max-angular-error-arcsec",
        str(args.max_angular_error_arcsec),
        "--gaia-max-magnitude",
        str(args.gaia_max_magnitude),
        "--global-match-radius-px",
        str(args.global_match_radius_px),
        "--minimum-global-matches",
        str(args.minimum_global_matches),
        "--max-candidate-reprojection-error-px",
        str(args.max_candidate_reprojection_error_px),
    ]
    if wcs is not None:
        command.extend(("--wcs", str(wcs)))
    for option, value in (
        ("--latitude", args.latitude),
        ("--longitude", args.longitude),
        ("--captured-at", args.captured_at),
        ("--utc-offset-hours", args.utc_offset_hours),
    ):
        if value is not None:
            command.extend((option, str(value)))

    print("06단계 최종 검증을 실행합니다.")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError(f"06단계 검증 실패(종료 코드 {completed.returncode})")
    stem = stem_from_matching(matching)
    return args.validation_output_dir.resolve() / stem / f"{stem}_validation.json"


def privacy_result(plate_report: dict[str, Any] | None) -> dict[str, Any]:
    if plate_report is None:
        return {
            "status": "not_available",
            "summary": "07단계 Plate Solving 보고서가 없습니다.",
        }
    if plate_report.get("backend") == "local":
        return {
            "status": "local_only",
            "summary": "로컬 Plate Solver를 사용하여 외부 서버 업로드가 없습니다.",
            "upload_copy_sanitized": None,
            "original_file_unchanged": True,
            "sensitive_values_recorded_in_report": False,
            "publicly_visible": None,
        }
    privacy = plate_report.get("privacy")
    if not isinstance(privacy, dict):
        return {
            "status": "legacy_unknown",
            "summary": "이 결과는 개인정보 보호 기록 기능 추가 전에 생성되었습니다.",
            "publicly_visible": plate_report.get("publicly_visible"),
        }
    sanitized = privacy.get("upload_copy_sanitized")
    status = "protected" if sanitized is True else "metadata_upload_allowed" if sanitized is False else "unknown"
    summary = {
        "protected": "메타데이터를 제거한 임시 복사본이 업로드되었습니다.",
        "metadata_upload_allowed": "사용자 옵션에 따라 원본 메타데이터 업로드가 허용되었습니다.",
        "unknown": "기존 Nova 작업이어서 당시 업로드 보호 여부를 확인할 수 없습니다.",
    }[status]
    # Presence flags are safe to retain; actual GPS/time values are deliberately excluded.
    return {
        "status": status,
        "summary": summary,
        "upload_copy_sanitized": sanitized,
        "original_file_unchanged": privacy.get("original_file_unchanged"),
        "temporary_copy_deleted": privacy.get("temporary_copy_deleted"),
        "gps_metadata_detected": privacy.get("gps_metadata_detected"),
        "datetime_metadata_detected": privacy.get("datetime_metadata_detected"),
        "sensitive_values_recorded_in_report": False,
        "publicly_visible": plate_report.get("publicly_visible"),
    }


def image_quality_evidence(stem: str, image_path: Path) -> dict[str, Any]:
    detection_path = DEFAULT_DETECTION_ROOT / stem / f"{stem}_stars.json"
    detection: dict[str, Any] | None = None
    if detection_path.is_file():
        detection = load_json(detection_path)
    image = read_image(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if max(gray.shape) > 1200:
        scale = 1200 / max(gray.shape)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    analyzed_fraction = 1.0
    if detection:
        analyzed_fraction = min(
            1.0,
            float(detection.get("analyzed_sky_height_original", image.shape[0]))
            / max(image.shape[0], 1),
        )
    sky = gray[: max(1, round(gray.shape[0] * analyzed_fraction))]
    blurred = cv2.GaussianBlur(sky, (0, 0), sigmaX=8.0, sigmaY=8.0)
    high_frequency = sky.astype(np.float32) - blurred.astype(np.float32)
    stars = detection.get("stars", []) if detection else []
    contrasts = [float(item.get("local_contrast", 0)) for item in stars]
    return {
        "detection_file": str(detection_path) if detection_path.is_file() else None,
        "detected_stars": int(detection.get("detected_stars", len(stars))) if detection else None,
        "minimum_usable_stars": int(detection.get("minimum_usable_stars", 7)) if detection else 7,
        "usable_for_graph": detection.get("usable_for_graph") if detection else None,
        "maximum_star_limit_reached": detection.get("maximum_star_limit_reached") if detection else None,
        "sky_brightness_mean": round(float(np.mean(sky)), 4),
        "sky_brightness_std": round(float(np.std(sky)), 4),
        "sky_high_frequency_std": round(float(np.std(high_frequency)), 4),
        "median_star_contrast": round(float(np.median(contrasts)), 4) if contrasts else None,
    }


def failure_assessment(
    matching: dict[str, Any],
    validation: dict[str, Any],
    plate_report: dict[str, Any] | None,
    quality: dict[str, Any],
) -> dict[str, Any]:
    codes: list[str] = []
    reasons: list[str] = []
    detected = quality.get("detected_stars")
    minimum = int(quality.get("minimum_usable_stars") or 7)
    if detected is not None and detected < minimum:
        codes.append("too_few_stars")
        reasons.append(f"별 후보가 {detected}개로 최소 기준 {minimum}개보다 적습니다.")

    brightness = float(quality.get("sky_brightness_mean") or 0)
    high_frequency = float(quality.get("sky_high_frequency_std") or 0)
    # Conservative heuristic: only label cloudy when the sky is bright/flat and
    # there are few point sources. Borderline cases remain ambiguous.
    cloudy = detected is not None and detected < 30 and (
        (brightness >= 35 and high_frequency < 12)
        or (detected < 15 and quality.get("sky_brightness_std", 999) < 12)
    )
    if cloudy:
        codes.append("cloudy")
        reasons.append("밝고 평탄한 하늘인데 점광원 수가 적어 구름 가능성이 높습니다.")

    wcs = validation.get("wcs_validation", {})
    global_wcs = wcs.get("global_reprojection", {})
    plate_failed = bool(plate_report and plate_report.get("status") == "failed")
    if global_wcs.get("status") == "fail":
        plate_failed = True
    if plate_failed:
        codes.append("plate_solve_failed")
        reasons.append("Plate Solving 결과가 없거나 사진 전체 WCS 재투영에 실패했습니다.")
    elif plate_report is None and wcs.get("status") == "not_available":
        codes.append("plate_solve_not_run")
        reasons.append("Plate Solving이 아직 실행되지 않았습니다.")

    results = matching.get("results", [])
    confirmed = bool(validation.get("decision", {}).get("confirmed"))
    candidate_reprojection = wcs.get("candidate_reprojection", {})
    ambiguous = (
        not confirmed
        and bool(results)
        and not plate_failed
        and (
            matching.get("decision", {}).get("confidence") in {"low", "medium"}
            or float(matching.get("decision", {}).get("best_second_score_margin", 0)) < 8
            or candidate_reprojection.get("status") in {"fail", "inconclusive"}
            or wcs.get("status") in {"inconclusive", "fail"}
        )
    )
    if ambiguous:
        codes.append("ambiguous")
        reasons.append("상위 후보를 다른 별자리와 구분하거나 WCS로 확정하기 어렵습니다.")
    if not results:
        codes.append("no_candidate")
        reasons.append("그래프 매칭에서 별자리 후보를 찾지 못했습니다.")

    priority = (
        "too_few_stars",
        "cloudy",
        "plate_solve_failed",
        "no_candidate",
        "ambiguous",
        "plate_solve_not_run",
    )
    primary = next((code for code in priority if code in codes), None)
    if confirmed:
        status = "pass"
        primary = None
        codes = []
        reasons = []
    elif primary in {"too_few_stars", "cloudy", "plate_solve_failed", "no_candidate"}:
        status = "failed"
    elif primary == "ambiguous":
        status = "ambiguous"
    else:
        status = "incomplete"
    return {
        "status": status,
        "primary_code": primary,
        "codes": codes,
        "reasons": reasons,
        "quality_evidence": quality,
    }


def read_image(path: Path) -> np.ndarray:
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"이미지를 읽을 수 없습니다: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 94])
    if not success:
        raise RuntimeError(f"이미지 저장에 실패했습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(path)


def create_final_image(
    validated_image: Path,
    candidate: dict[str, Any] | None,
    validation: dict[str, Any],
    privacy: dict[str, Any],
    failure: dict[str, Any],
    calibration: dict[str, Any] | None,
) -> np.ndarray:
    base = read_image(validated_image)
    panel_height = max(150, int(base.shape[0] * 0.09))
    panel = np.zeros((panel_height, base.shape[1], 3), dtype=np.uint8)
    confirmed = bool(validation["decision"].get("confirmed"))
    name = "No candidate" if candidate is None else f"{candidate['native_name']} ({candidate['iau']})"
    headline = f"FINAL: {name} | {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}"
    structural = validation.get("structural_validation", {}).get("status", "unknown")
    wcs_status = validation.get("wcs_validation", {}).get("status", "unknown")
    evidence = f"structure={structural} | WCS={wcs_status} | privacy={privacy['status']}"
    lines = [headline, evidence]
    if failure.get("primary_code"):
        lines.append(f"failure={failure['primary_code']} | codes={','.join(failure['codes'])}")
    if calibration:
        lines.append(
            "plate center RA/DEC={:.4f}, {:.4f} | scale={:.3f} arcsec/px".format(
                float(calibration.get("ra", 0)),
                float(calibration.get("dec", 0)),
                float(calibration.get("pixscale", 0)),
            )
        )
    font_scale = max(0.55, min(1.0, base.shape[1] / 1500.0))
    y = int(42 * font_scale)
    for index, line in enumerate(lines):
        color = (60, 230, 90) if index == 0 and confirmed else (235, 235, 235)
        cv2.putText(
            panel,
            line,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            max(1, int(2 * font_scale)),
            cv2.LINE_AA,
        )
        y += int(43 * font_scale)
    return np.vstack((panel, base))


def text_report(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    candidate = payload.get("candidate")
    candidate_text = "없음" if candidate is None else f"{candidate['native_name']} ({candidate['iau']})"
    calibration = payload.get("plate_solving", {}).get("calibration")
    lines = [
        "별자리 최종 인식 결과",
        f"후보: {candidate_text}",
        f"판정: {decision['status']}",
        f"확정 여부: {'예' if decision['confirmed'] else '아니오'}",
        f"이유: {decision['reason']}",
        f"구조 검증: {payload['evidence']['structural_status']}",
        f"WCS 검증: {payload['evidence']['wcs_status']}",
        f"업로드 개인정보 보호: {payload['privacy']['status']} - {payload['privacy']['summary']}",
        f"실패 판정: {payload['failure_assessment']['primary_code'] or '없음'}",
    ]
    if calibration:
        lines.append(
            f"Plate Solving 중심 RA/DEC: {calibration.get('ra')}, {calibration.get('dec')}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    matching_path = args.matching.resolve()
    matching = load_json(matching_path)
    if "decision" not in matching or "results" not in matching:
        raise ValueError("05단계 *_matching.json 형식이 아닙니다.")
    stem = stem_from_matching(matching_path)
    wcs = find_wcs(stem, args.wcs, args.wcs_root)
    print(f"WCS: {wcs if wcs else '없음(후보 확정 불가)'}")

    validation_path = run_validation(args, matching_path, wcs)
    validation = load_json(validation_path)
    candidate = validation.get("candidate")

    plate_report_path = args.wcs_root.resolve() / stem / f"{stem}_plate_solve.json"
    plate_report = load_json(plate_report_path) if plate_report_path.is_file() else None
    privacy = privacy_result(plate_report)
    confirmed = bool(validation.get("decision", {}).get("confirmed"))
    image_path = Path(str(matching.get("image"))).resolve()
    quality = image_quality_evidence(stem, image_path)
    failure = failure_assessment(matching, validation, plate_report, quality)
    final_status = "recognized" if confirmed else failure["status"]
    output_folder = args.output_dir.resolve() / stem
    output_folder.mkdir(parents=True, exist_ok=True)
    final_json = output_folder / f"{stem}_final.json"
    final_text = output_folder / f"{stem}_final.txt"
    final_image = output_folder / f"{stem}_final.jpg"
    validated_image = args.validation_output_dir.resolve() / stem / f"{stem}_validated.jpg"

    payload: dict[str, Any] = {
        "source_matching": str(matching_path),
        "source_validation": str(validation_path),
        "source_wcs": str(wcs) if wcs else None,
        "source_plate_solve_report": str(plate_report_path) if plate_report else None,
        "image": matching.get("image"),
        "candidate": candidate,
        "decision": {
            "status": final_status,
            "confirmed": confirmed,
            "reason": validation["decision"]["reason"],
        },
        "evidence": {
            "graph_confidence": matching.get("decision", {}).get("confidence"),
            "structural_status": validation.get("structural_validation", {}).get("status"),
            "horizon_status": validation.get("horizon_visibility", {}).get("status"),
            "wcs_status": validation.get("wcs_validation", {}).get("status"),
        },
        "plate_solving": {
            "backend": plate_report.get("backend") if plate_report else None,
            "job_id": plate_report.get("job_id") if plate_report else None,
            "calibration": plate_report.get("calibration") if plate_report else None,
        },
        "privacy": privacy,
        "failure_assessment": failure,
    }
    final_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    final_text.write_text(text_report(payload), encoding="utf-8")
    image = create_final_image(
        validated_image,
        candidate,
        validation,
        privacy,
        failure,
        payload["plate_solving"]["calibration"],
    )
    write_image(final_image, image)

    print(f"최종 후보: {candidate['iau'] + ' / ' + candidate['native_name'] if candidate else '없음'}")
    print(f"최종 판정: {final_status}")
    print(
        "실패 판정: "
        f"{failure['primary_code'] or '없음'}"
        + (f" ({', '.join(failure['codes'])})" if failure["codes"] else "")
    )
    print(f"개인정보 보호 상태: {privacy['status']} - {privacy['summary']}")
    print(f"final_json: {final_json}")
    print(f"final_text: {final_text}")
    print(f"final_image: {final_image}")


if __name__ == "__main__":
    main()
