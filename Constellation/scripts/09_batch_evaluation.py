"""Evaluate many constellation matching results through the final recognition stage."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_SCRIPT = PROJECT_ROOT / "scripts" / "08_final_recognition.py"
OVERLAY_SCRIPT = PROJECT_ROOT / "scripts" / "11_wcs_constellation_overlay.py"
DEFAULT_MATCHING_DIR = PROJECT_ROOT / "data" / "results" / "graph_matching"
DEFAULT_WCS_ROOT = PROJECT_ROOT / "data" / "wcs"
DEFAULT_VALIDATION_ROOT = PROJECT_ROOT / "data" / "results" / "match_validation"
DEFAULT_FINAL_ROOT = PROJECT_ROOT / "data" / "results" / "final_recognition"
DEFAULT_OVERLAY_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "batch_evaluation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matching-dir", type=Path, default=DEFAULT_MATCHING_DIR)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        help="stem, expected_iau, should_recognize 열을 가진 선택적 정답 CSV",
    )
    parser.add_argument("--wcs-root", type=Path, default=DEFAULT_WCS_ROOT)
    parser.add_argument("--validation-output-dir", type=Path, default=DEFAULT_VALIDATION_ROOT)
    parser.add_argument("--final-output-dir", type=Path, default=DEFAULT_FINAL_ROOT)
    parser.add_argument("--overlay-output-dir", type=Path, default=DEFAULT_OVERLAY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, help="앞에서부터 처리할 최대 파일 수")
    parser.add_argument(
        "--skip-final-run",
        action="store_true",
        help="08단계를 실행하지 않고 기존 *_final.json만 평가",
    )
    parser.add_argument("--verbose", action="store_true", help="각 08단계 전체 출력을 표시")
    parser.add_argument("--minimum-altitude-deg", type=float, default=-5.0)
    parser.add_argument("--max-angular-error-arcsec", type=float, default=180.0)
    parser.add_argument("--gaia-max-magnitude", type=float, default=8.0)
    parser.add_argument("--global-match-radius-px", type=float, default=5.0)
    parser.add_argument("--minimum-global-matches", type=int, default=12)
    parser.add_argument("--max-candidate-reprojection-error-px", type=float, default=5.0)
    return parser.parse_args()


def parse_bool(value: str | None, default: bool | None = None) -> bool | None:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "예", "성공"}:
        return True
    if normalized in {"0", "false", "no", "n", "아니오", "실패"}:
        return False
    raise ValueError(f"should_recognize 값은 true/false여야 합니다: {value}")


def expected_set(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        item.strip().upper()
        for item in re.split(r"[|;,]", value)
        if item.strip()
    }


def load_ground_truth(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"정답 CSV를 찾을 수 없습니다: {path}")
    truth: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or "stem" not in reader.fieldnames:
            raise ValueError("정답 CSV에는 stem 열이 필요합니다.")
        for line_number, row in enumerate(reader, start=2):
            stem = (row.get("stem") or "").strip()
            if not stem:
                raise ValueError(f"정답 CSV {line_number}행의 stem이 비어 있습니다.")
            if stem in truth:
                raise ValueError(f"정답 CSV에 stem이 중복됩니다: {stem}")
            expected = expected_set(row.get("expected_iau"))
            should_recognize = parse_bool(row.get("should_recognize"), bool(expected))
            if should_recognize and not expected:
                raise ValueError(
                    f"{stem}: should_recognize=true이면 expected_iau가 필요합니다."
                )
            truth[stem] = {
                "expected": expected,
                "should_recognize": bool(should_recognize),
                "notes": (row.get("notes") or "").strip(),
            }
    return truth


def discover_matching_files(root: Path, limit: int | None) -> list[Path]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"매칭 결과 폴더를 찾을 수 없습니다: {root}")
    files = sorted(root.rglob("*_matching.json"), key=lambda path: str(path).lower())
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다.")
        files = files[:limit]
    if not files:
        raise FileNotFoundError(f"*_matching.json 파일이 없습니다: {root}")
    return files


def stem_from_matching(path: Path) -> str:
    stem = path.stem
    return stem[:-9] if stem.endswith("_matching") else stem


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wcs_available(stem: str, root: Path) -> bool:
    folder = root.resolve() / stem
    return (folder / f"{stem}.new").is_file() or (folder / f"{stem}.wcs").is_file()


def run_final_stage(args: argparse.Namespace, matching: Path) -> tuple[bool, str]:
    command = [
        sys.executable,
        str(FINAL_SCRIPT),
        str(matching),
        "--wcs-root",
        str(args.wcs_root.resolve()),
        "--validation-output-dir",
        str(args.validation_output_dir.resolve()),
        "--output-dir",
        str(args.final_output_dir.resolve()),
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
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    output = "\n".join(
        part.rstrip() for part in (completed.stdout, completed.stderr) if part
    )
    if args.verbose and output:
        print(output)
    return completed.returncode == 0, output


def final_json_path(stem: str, root: Path) -> Path:
    return root.resolve() / stem / f"{stem}_final.json"


def overlay_json_path(stem: str, root: Path) -> Path:
    return root.resolve() / stem / f"{stem}_wcs_constellations.json"


def run_overlay_stage(args: argparse.Namespace, image: Path) -> tuple[bool, str]:
    command = [
        sys.executable,
        str(OVERLAY_SCRIPT),
        str(image),
        "--wcs-root",
        str(args.wcs_root.resolve()),
        "--output-dir",
        str(args.overlay_output_dir.resolve()),
    ]
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
    if args.verbose and output:
        print(output)
    return completed.returncode == 0, output


def error_tail(output: str, maximum: int = 500) -> str:
    compact = " | ".join(line.strip() for line in output.splitlines() if line.strip())
    return compact[-maximum:]


def build_row(
    stem: str,
    matching: Path,
    final: dict[str, Any],
    truth: dict[str, Any] | None,
    has_wcs: bool,
    overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = final.get("candidate") or {}
    overlay_recognized = bool(
        overlay and overlay.get("decision", {}).get("status") == "recognized"
    )
    if overlay_recognized:
        predicted_values = [
            str(value).upper() for value in overlay["decision"].get("constellations", [])
        ]
        selected_names = [item.get("native_name") for item in overlay.get("selected", [])]
    else:
        predicted_values = [str(candidate.get("iau") or "").upper()] if candidate.get("iau") else []
        selected_names = [candidate.get("native_name")] if candidate.get("native_name") else []
    predicted = "|".join(predicted_values)
    confirmed = overlay_recognized or bool(final.get("decision", {}).get("confirmed"))
    failure = {} if overlay_recognized else final.get("failure_assessment", {})
    expected = truth["expected"] if truth else set()
    should_recognize = truth["should_recognize"] if truth else None
    candidate_correct: bool | None = None
    final_correct: bool | None = None
    if truth is not None:
        candidate_correct = bool(set(predicted_values) & expected) if expected else not predicted_values
        if should_recognize:
            final_correct = confirmed and predicted in expected
        else:
            final_correct = not confirmed
    return {
        "stem": stem,
        "processing_status": "success",
        "image": final.get("image"),
        "matching_json": str(matching),
        "wcs_available": has_wcs,
        "predicted_iau": predicted or None,
        "predicted_name": "|".join(str(value) for value in selected_names),
        "graph_confidence": final.get("evidence", {}).get("graph_confidence"),
        "structural_status": final.get("evidence", {}).get("structural_status"),
        "wcs_status": "overlay_pass" if overlay_recognized else final.get("evidence", {}).get("wcs_status"),
        "final_status": "recognized" if overlay_recognized else final.get("decision", {}).get("status"),
        "confirmed": confirmed,
        "privacy_status": final.get("privacy", {}).get("status"),
        "failure_code": failure.get("primary_code"),
        "failure_codes": "|".join(failure.get("codes", [])),
        "expected_iau": "|".join(sorted(expected)) if truth else None,
        "should_recognize": should_recognize,
        "candidate_correct": candidate_correct,
        "final_correct": final_correct,
        "notes": truth.get("notes") if truth else None,
        "error": None,
    }


def failure_row(
    stem: str,
    matching: Path,
    truth: dict[str, Any] | None,
    has_wcs: bool,
    error: str,
) -> dict[str, Any]:
    return {
        "stem": stem,
        "processing_status": "failed",
        "image": None,
        "matching_json": str(matching),
        "wcs_available": has_wcs,
        "predicted_iau": None,
        "predicted_name": None,
        "graph_confidence": None,
        "structural_status": None,
        "wcs_status": None,
        "final_status": None,
        "confirmed": False,
        "privacy_status": None,
        "failure_code": "pipeline_error",
        "failure_codes": "pipeline_error",
        "expected_iau": "|".join(sorted(truth["expected"])) if truth else None,
        "should_recognize": truth["should_recognize"] if truth else None,
        "candidate_correct": None,
        "final_correct": False if truth else None,
        "notes": truth.get("notes") if truth else None,
        "error": error,
    }


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def compute_metrics(rows: list[dict[str, Any]], truth_count: int) -> dict[str, Any]:
    successful = [row for row in rows if row["processing_status"] == "success"]
    labeled = [row for row in rows if row["should_recognize"] is not None]
    positives = [row for row in labeled if row["should_recognize"]]
    confirmed_labeled = [row for row in labeled if row["confirmed"]]
    correct_confirmed = [
        row
        for row in confirmed_labeled
        if row["should_recognize"] and row["candidate_correct"] is True
    ]
    false_confirmed = [
        row
        for row in confirmed_labeled
        if not row["should_recognize"] or row["candidate_correct"] is not True
    ]
    top1_correct = sum(row["candidate_correct"] is True for row in positives)
    final_correct = sum(row["final_correct"] is True for row in labeled)
    return {
        "discovered": len(rows),
        "processed_success": len(successful),
        "processed_failed": len(rows) - len(successful),
        "processing_success_rate": safe_ratio(len(successful), len(rows)),
        "wcs_available": sum(bool(row["wcs_available"]) for row in rows),
        "wcs_availability_rate": safe_ratio(
            sum(bool(row["wcs_available"]) for row in rows), len(rows)
        ),
        "recognized": sum(bool(row["confirmed"]) for row in successful),
        "recognition_rate": safe_ratio(
            sum(bool(row["confirmed"]) for row in successful), len(successful)
        ),
        "ground_truth_rows_loaded": truth_count,
        "evaluated_with_ground_truth": len(labeled),
        "positive_ground_truth": len(positives),
        "top1_candidate_accuracy": safe_ratio(top1_correct, len(positives)),
        "final_decision_accuracy": safe_ratio(final_correct, len(labeled)),
        "confirmed_precision": safe_ratio(len(correct_confirmed), len(confirmed_labeled)),
        "recognition_recall": safe_ratio(len(correct_confirmed), len(positives)),
        "confirmed_coverage": safe_ratio(len(confirmed_labeled), len(labeled)),
        "false_confirmations": len(false_confirmed),
        "false_confirmation_stems": [row["stem"] for row in false_confirmed],
        "failure_codes": dict(
            sorted(Counter(row["failure_code"] for row in rows if row["failure_code"]).items())
        ),
        "predicted_constellations": dict(
            sorted(
                Counter(
                    value
                    for row in successful
                    for value in str(row["predicted_iau"] or "").split("|")
                    if value
                ).items()
            )
        ),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summary_text(metrics: dict[str, Any]) -> str:
    def percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value * 100:.2f}%"

    lines = [
        "별자리 배치 평가 결과",
        f"발견: {metrics['discovered']}장",
        f"처리 성공: {metrics['processed_success']}장 ({percent(metrics['processing_success_rate'])})",
        f"WCS 보유: {metrics['wcs_available']}장 ({percent(metrics['wcs_availability_rate'])})",
        f"별자리 확정: {metrics['recognized']}장 ({percent(metrics['recognition_rate'])})",
        f"정답 평가: {metrics['evaluated_with_ground_truth']}장",
        f"후보 Top-1 정확도: {percent(metrics['top1_candidate_accuracy'])}",
        f"최종 판정 정확도: {percent(metrics['final_decision_accuracy'])}",
        f"확정 정밀도: {percent(metrics['confirmed_precision'])}",
        f"인식 재현율: {percent(metrics['recognition_recall'])}",
        f"오확정: {metrics['false_confirmations']}장",
        "실패 유형: "
        + (
            ", ".join(f"{key}={value}" for key, value in metrics["failure_codes"].items())
            if metrics["failure_codes"]
            else "없음"
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    truth = load_ground_truth(args.ground_truth)
    matching_files = discover_matching_files(args.matching_dir, args.limit)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    print(f"배치 평가 대상: {len(matching_files)}장")
    for index, matching in enumerate(matching_files, start=1):
        stem = stem_from_matching(matching)
        item_truth = truth.get(stem)
        has_wcs = wcs_available(stem, args.wcs_root)
        print(f"[{index}/{len(matching_files)}] {stem} - WCS {'있음' if has_wcs else '없음'}")
        try:
            if not args.skip_final_run:
                succeeded, output = run_final_stage(args, matching)
                if not succeeded:
                    rows.append(failure_row(stem, matching, item_truth, has_wcs, error_tail(output)))
                    print("  처리 실패")
                    continue
            final_path = final_json_path(stem, args.final_output_dir)
            if not final_path.is_file():
                raise FileNotFoundError(f"최종 JSON이 없습니다: {final_path}")
            final = load_json(final_path)
            overlay = None
            overlay_path = overlay_json_path(stem, args.overlay_output_dir)
            if has_wcs:
                can_load_overlay = args.skip_final_run
                if not args.skip_final_run:
                    overlay_ok, overlay_output = run_overlay_stage(
                        args, Path(str(final["image"])).resolve()
                    )
                    can_load_overlay = overlay_ok
                    if not overlay_ok:
                        print(f"  11단계 오버레이 실패: {error_tail(overlay_output)}")
                if can_load_overlay and overlay_path.is_file():
                    overlay = load_json(overlay_path)
            row = build_row(stem, matching, final, item_truth, has_wcs, overlay)
            rows.append(row)
            print(
                f"  후보={row['predicted_iau'] or '없음'}, "
                f"판정={row['final_status']}, WCS={row['wcs_status']}"
            )
        except Exception as error:
            rows.append(failure_row(stem, matching, item_truth, has_wcs, str(error)))
            print(f"  처리 실패: {error}")

    missing_truth = sorted(set(truth) - {row["stem"] for row in rows})
    metrics = compute_metrics(rows, len(truth))
    report = {
        "matching_dir": str(args.matching_dir.resolve()),
        "ground_truth": str(args.ground_truth.resolve()) if args.ground_truth else None,
        "parameters": {
            "skip_final_run": args.skip_final_run,
            "minimum_altitude_deg": args.minimum_altitude_deg,
            "max_angular_error_arcsec": args.max_angular_error_arcsec,
            "gaia_max_magnitude": args.gaia_max_magnitude,
            "global_match_radius_px": args.global_match_radius_px,
            "minimum_global_matches": args.minimum_global_matches,
            "max_candidate_reprojection_error_px": args.max_candidate_reprojection_error_px,
        },
        "metrics": metrics,
        "ground_truth_without_matching_result": missing_truth,
        "rows": rows,
    }
    csv_path = output_dir / "batch_evaluation.csv"
    json_path = output_dir / "batch_evaluation.json"
    text_path = output_dir / "batch_evaluation_summary.txt"
    write_csv(csv_path, rows)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(summary_text(metrics), encoding="utf-8")

    print(summary_text(metrics).rstrip())
    if missing_truth:
        print(f"주의: 매칭 결과가 없는 정답 {len(missing_truth)}개: {', '.join(missing_truth)}")
    print(f"evaluation_csv: {csv_path}")
    print(f"evaluation_json: {json_path}")
    print(f"summary_txt: {text_path}")


if __name__ == "__main__":
    main()
