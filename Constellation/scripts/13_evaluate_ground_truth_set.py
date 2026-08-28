"""Run the end-to-end recognizer on the verified set and compute multi-label metrics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "10_end_to_end_pipeline.py"
DEFAULT_GROUND_TRUTH = (
    PROJECT_ROOT / "data" / "evaluation" / "verified_smartphone" / "ground_truth.csv"
)
PIPELINE_ROOT = PROJECT_ROOT / "data" / "results" / "pipeline"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "ground_truth_evaluation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--plate-backend", choices=("auto", "local", "nova"), default="nova")
    parser.add_argument("--plate-timeout-seconds", type=int, default=300)
    parser.add_argument("--nova-request-retries", type=int, default=3)
    parser.add_argument("--scale-lower", type=float, default=40.0)
    parser.add_argument("--scale-upper", type=float, default=110.0)
    parser.add_argument("--sky-fraction", type=float, default=1.0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-processing", action="store_true", help="기존 pipeline JSON만 평가")
    parser.add_argument("--force-local", action="store_true", help="03~05단계를 다시 실행")
    parser.add_argument(
        "--force-plate-solving",
        action="store_true",
        help="기존 WCS가 있어도 07단계를 다시 실행하고 외부 업로드할 수 있음",
    )
    parser.add_argument("--retry-failed", action="store_true", help="상태 파일의 완료된 실패 항목을 재실행")
    parser.add_argument("--dry-run", action="store_true", help="파일과 실행 계획만 검사")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def parse_bool(value: str, line_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"정답 CSV {line_number}행 should_recognize 값이 잘못됐습니다: {value}")


def label_set(value: str | None) -> set[str]:
    return {
        item.strip().upper()
        for item in re.split(r"[|;,]", value or "")
        if item.strip()
    }


def load_ground_truth(path: Path, limit: int | None) -> list[dict[str, Any]]:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"정답 CSV를 찾을 수 없습니다: {path}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"stem", "scene_id", "source_path", "expected_iau", "should_recognize"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"정답 CSV 필수 열이 없습니다: {', '.join(sorted(missing))}")
        for line_number, raw in enumerate(reader, start=2):
            stem = (raw.get("stem") or "").strip()
            if not stem or stem in seen:
                raise ValueError(f"정답 CSV {line_number}행 stem이 비었거나 중복입니다: {stem}")
            source = Path(raw["source_path"]).resolve()
            if not source.is_file():
                raise FileNotFoundError(f"평가 사진을 찾을 수 없습니다: {source}")
            expected = label_set(raw.get("expected_iau"))
            should_recognize = parse_bool(raw.get("should_recognize") or "", line_number)
            if should_recognize and not expected:
                raise ValueError(f"{stem}: 양성 정답의 expected_iau가 비어 있습니다.")
            rows.append(
                {
                    **raw,
                    "stem": stem,
                    "scene_id": (raw.get("scene_id") or stem).strip(),
                    "source_path": str(source),
                    "expected": expected,
                    "should_recognize_bool": should_recognize,
                }
            )
            seen.add(stem)
            if limit is not None and len(rows) >= limit:
                break
    if limit is not None and limit < 1:
        raise ValueError("--limit은 1 이상이어야 합니다.")
    if not rows:
        raise ValueError("평가할 정답 행이 없습니다.")
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pipeline_path(stem: str) -> Path:
    return PIPELINE_ROOT / stem / f"{stem}_pipeline.json"


def same_source(report_path: Path, source: Path) -> bool:
    if not report_path.is_file():
        return False
    try:
        return Path(load_json(report_path).get("image", "")).resolve() == source.resolve()
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def run_pipeline(item: dict[str, Any], args: argparse.Namespace, log_path: Path) -> tuple[int, str]:
    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        item["source_path"],
        "--plate-backend",
        args.plate_backend,
        "--plate-timeout-seconds",
        str(args.plate_timeout_seconds),
        "--nova-request-retries",
        str(args.nova_request_retries),
        "--scale-units",
        "degwidth",
        "--scale-lower",
        str(args.scale_lower),
        "--scale-upper",
        str(args.scale_upper),
        "--sky-fraction",
        str(args.sky_fraction),
    ]
    if args.force_local:
        command.append("--force-local")
    if args.force_plate_solving:
        command.append("--force-plate-solving")
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output + ("\n" if output else ""), encoding="utf-8")
    if args.verbose and output:
        print(output)
    return completed.returncode, output


def ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return 0.0 if precision == 0 or recall == 0 else None
    return round(2 * precision * recall / (precision + recall), 6)


def evaluate_item(item: dict[str, Any], processing_status: str, error: str = "") -> dict[str, Any]:
    report_path = pipeline_path(item["stem"])
    report: dict[str, Any] = {}
    if same_source(report_path, Path(item["source_path"])):
        report = load_json(report_path)
    outcome = report.get("outcome", {})
    predicted = label_set("|".join(str(value) for value in outcome.get("constellations", [])))
    confirmed = bool(outcome.get("confirmed")) and outcome.get("status") == "recognized"
    if confirmed and not predicted and outcome.get("candidate"):
        predicted = {str(outcome["candidate"]).upper()}
    if not confirmed:
        predicted = set()
    expected = item["expected"]
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    sample_f1 = f1(precision, recall)
    positive = item["should_recognize_bool"]
    evaluable = bool(report)
    exact_match = evaluable and (confirmed and predicted == expected if positive else not confirmed)
    overlap_match = evaluable and (bool(predicted & expected) if positive else not confirmed)
    return {
        "sample_id": item.get("sample_id") or item["stem"],
        "stem": item["stem"],
        "scene_id": item["scene_id"],
        "frame_role": item.get("frame_role"),
        "source_path": item["source_path"],
        "evaluation_type": item.get("evaluation_type"),
        "evaluation_scope": item.get("evaluation_scope") or "recognition",
        "label_semantics": item.get("label_semantics") or "legacy",
        "processing_status": processing_status,
        "expected_iau": "|".join(sorted(expected)),
        "predicted_iau": "|".join(sorted(predicted)),
        "should_recognize": positive,
        "recognized": confirmed,
        "exact_match": exact_match,
        "overlap_match": overlap_match,
        "label_tp": tp,
        "label_fp": fp,
        "label_fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": sample_f1,
        "failure_code": outcome.get("failure_code") or ("pipeline_error" if error else ""),
        "failure_codes": "|".join(str(value) for value in outcome.get("failure_codes", [])),
        "recognition_method": outcome.get("recognition_method"),
        "pipeline_json": str(report_path) if report else "",
        "error": error,
    }


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [row for row in rows if row["should_recognize"]]
    negatives = [row for row in rows if not row["should_recognize"]]
    tp = sum(row["label_tp"] for row in rows)
    fp = sum(row["label_fp"] for row in rows)
    fn = sum(row["label_fn"] for row in rows)
    micro_precision = ratio(tp, tp + fp)
    micro_recall = ratio(tp, tp + fn)
    macro_values = [row["f1"] for row in positives if row["f1"] is not None]
    strict_correct = sum(bool(row["exact_match"]) for row in rows)
    overlap_correct = sum(bool(row["overlap_match"]) for row in rows)
    all_expected_found = sum(
        bool(row["recognized"]) and row["label_fn"] == 0 for row in positives
    )
    return {
        "samples": len(rows),
        "scenes": len({row["scene_id"] for row in rows}),
        "positive_samples": len(positives),
        "negative_samples": len(negatives),
        "processing_success": sum(row["processing_status"] == "success" for row in rows),
        "recognized": sum(bool(row["recognized"]) for row in rows),
        "strict_exact_accuracy": ratio(strict_correct, len(rows)),
        "positive_exact_accuracy": ratio(sum(bool(row["exact_match"]) for row in positives), len(positives)),
        "positive_overlap_accuracy": ratio(sum(bool(row["overlap_match"]) for row in positives), len(positives)),
        "all_verified_labels_found_rate": ratio(all_expected_found, len(positives)),
        "any_verified_label_found_rate": ratio(overlap_correct - sum(bool(row["overlap_match"]) for row in negatives), len(positives)),
        "negative_rejection_accuracy": ratio(sum(bool(row["exact_match"]) for row in negatives), len(negatives)),
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": f1(micro_precision, micro_recall),
        "macro_f1_positive": round(sum(macro_values) / len(macro_values), 6) if macro_values else None,
        "label_tp": tp,
        "label_fp": fp,
        "label_fn": fn,
        "failure_codes": dict(sorted(Counter(row["failure_code"] for row in rows if row["failure_code"]).items())),
    }


def scene_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["scene_id"]].append(row)
    result = []
    for scene_id, items in sorted(grouped.items()):
        result.append(
            {
                "scene_id": scene_id,
                "samples": len(items),
                "evaluation_type": items[0]["evaluation_type"],
                "expected_iau": items[0]["expected_iau"],
                "recognized": sum(bool(item["recognized"]) for item in items),
                "exact_correct": sum(bool(item["exact_match"]) for item in items),
                "overlap_correct": sum(bool(item["overlap_match"]) for item in items),
                "exact_accuracy": ratio(sum(bool(item["exact_match"]) for item in items), len(items)),
                "overlap_accuracy": ratio(sum(bool(item["overlap_match"]) for item in items), len(items)),
                "predictions": ";".join(sorted(Counter(item["predicted_iau"] for item in items).keys())),
            }
        )
    return result


def write_csv(
    path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None
) -> None:
    if fieldnames is None:
        if not rows:
            return
        fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def summary_text(metrics: dict[str, Any]) -> str:
    return "\n".join(
        [
            "정답 평가셋 전체 파이프라인 결과",
            f"평가: {metrics['samples']}장 / {metrics['scenes']}장면",
            f"처리 성공: {metrics['processing_success']}장",
            f"별자리 확정: {metrics['recognized']}장",
            f"엄격한 전체 정확도: {percent(metrics['strict_exact_accuracy'])}",
            f"양성 exact 정확도: {percent(metrics['positive_exact_accuracy'])}",
            f"양성 overlap 정확도: {percent(metrics['positive_overlap_accuracy'])}",
            f"모든 검증 라벨 발견률(주 지표): {percent(metrics['all_verified_labels_found_rate'])}",
            f"하나 이상 검증 라벨 발견률: {percent(metrics['any_verified_label_found_rate'])}",
            f"음성 거부 정확도: {percent(metrics['negative_rejection_accuracy'])}",
            f"참고용 micro Precision(라벨 비포괄): {percent(metrics['micro_precision'])}",
            f"다중 라벨 micro Recall: {percent(metrics['micro_recall'])}",
            f"다중 라벨 micro F1: {percent(metrics['micro_f1'])}",
            f"양성 macro F1: {percent(metrics['macro_f1_positive'])}",
        ]
    ) + "\n"


def main() -> None:
    args = parse_args()
    items = load_ground_truth(args.ground_truth, args.limit)
    output_dir = args.output_dir.resolve()
    state_path = output_dir / "evaluation_state.json"
    print(f"평가 대상: {len(items)}장 / {len({item['scene_id'] for item in items})}장면")
    existing = sum(same_source(pipeline_path(item["stem"]), Path(item["source_path"])) for item in items)
    print(f"기존 파이프라인 결과: {existing}장, 신규 처리 필요: {len(items) - existing}장")
    if args.dry_run:
        print("드라이런 완료: 사진·정답·중복·실행 계획이 정상입니다.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {"items": {}}
    if state_path.is_file():
        state = load_json(state_path)
        state.setdefault("items", {})

    rows_by_stem: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items, start=1):
        stem = item["stem"]
        prior = state["items"].get(stem, {})
        report_exists = same_source(pipeline_path(stem), Path(item["source_path"]))
        retryable_positive_failure = bool(
            args.retry_failed
            and prior.get("should_recognize")
            and prior.get("failure_code") in {"plate_solve_failed", "pipeline_error"}
        )
        should_run = not args.skip_processing and (
            not report_exists
            or args.force_local
            or args.force_plate_solving
            or retryable_positive_failure
        )
        print(f"[{index}/{len(items)}] {stem} - {'실행' if should_run else '기존 결과 평가'}")
        error = ""
        return_code = 0
        if should_run:
            return_code, output = run_pipeline(item, args, output_dir / "logs" / f"{stem}.log")
            if return_code != 0:
                error = " | ".join(line.strip() for line in output.splitlines() if line.strip())[-800:]
        elif not report_exists:
            error = "pipeline JSON이 없습니다. --skip-processing을 제거하고 실행하세요."
        processing_status = "success" if same_source(pipeline_path(stem), Path(item["source_path"])) else "missing"
        if return_code != 0 and processing_status != "success":
            processing_status = "failed"
        row = evaluate_item(item, processing_status, error)
        rows_by_stem[stem] = row
        state["items"][stem] = row
        state["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"  정답={row['expected_iau'] or '인식실패'}, 예측={row['predicted_iau'] or '인식실패'}, "
            f"exact={'예' if row['exact_match'] else '아니오'}"
        )

    rows = [rows_by_stem[item["stem"]] for item in items]
    scenes = scene_rows(rows)
    metrics = compute_metrics(rows)
    wrong = [row for row in rows if not row["exact_match"]]
    write_csv(output_dir / "evaluation_results.csv", rows)
    write_csv(output_dir / "scene_metrics.csv", scenes)
    write_csv(output_dir / "wrong_predictions.csv", wrong, list(rows[0]))
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ground_truth": str(args.ground_truth.resolve()),
        "parameters": {
            "plate_backend": args.plate_backend,
            "plate_timeout_seconds": args.plate_timeout_seconds,
            "nova_request_retries": args.nova_request_retries,
            "scale_lower": args.scale_lower,
            "scale_upper": args.scale_upper,
            "sky_fraction": args.sky_fraction,
            "skip_processing": args.skip_processing,
        },
        "metrics": metrics,
        "scenes": scenes,
    }
    (output_dir / "evaluation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "evaluation_summary.txt").write_text(summary_text(metrics), encoding="utf-8")
    print(summary_text(metrics).rstrip())
    print(f"results_csv: {output_dir / 'evaluation_results.csv'}")
    print(f"scene_metrics: {output_dir / 'scene_metrics.csv'}")
    print(f"wrong_predictions: {output_dir / 'wrong_predictions.csv'}")
    print(f"report_json: {output_dir / 'evaluation_report.json'}")


if __name__ == "__main__":
    main()
