"""Analyze stage-50 results without running plate solving again."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "results" / "representative12_evaluation" / "evaluation_results.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "representative12_evaluation" / "failure_analysis.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def resolution_bucket(row: dict[str, Any]) -> str:
    side = min(as_float(row.get("width")), as_float(row.get("height")))
    if side < 800:
        return "600-799"
    if side < 1200:
        return "800-1199"
    if side < 2000:
        return "1200-1999"
    return "2000+"


def rate(part: int, total: int) -> float | None:
    return round(part / total * 100, 2) if total else None


def group_stats(rows: list[dict[str, Any]], key) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(key(row))].append(row)
    output: dict[str, Any] = {}
    for name, items in sorted(groups.items()):
        solved = sum(row.get("plate_status") == "success" for row in items)
        timeouts = sum(row.get("failure_type") in {"TimeoutError", "BatchTimeout"} for row in items)
        output[name] = {
            "images": len(items),
            "plate_solved": solved,
            "plate_solve_rate": rate(solved, len(items)),
            "timeouts": timeouts,
            "timeout_rate": rate(timeouts, len(items)),
        }
    return output


def main() -> None:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f"50번 평가 결과가 없습니다: {args.input}")
    with args.input.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    positives = [row for row in rows if not as_bool(row.get("is_negative"))]
    negatives = [row for row in rows if as_bool(row.get("is_negative"))]
    solved_positives = [row for row in positives if row.get("plate_status") == "success"]
    correct_positives = [row for row in positives if as_bool(row.get("expected_hit"))]
    false_positive_negatives = [row for row in negatives if row.get("predicted_iau")]
    elapsed = [as_float(row.get("elapsed_seconds")) for row in rows]
    failures = Counter(row.get("failure_type") for row in rows if row.get("failure_type"))

    report = {
        "processed": len(rows),
        "runtime": {
            "total_hours": round(sum(elapsed) / 3600, 2),
            "average_seconds": round(mean(elapsed), 2) if elapsed else None,
            "median_seconds": round(median(elapsed), 2) if elapsed else None,
        },
        "positive_pipeline": {
            "images": len(positives),
            "plate_solved": len(solved_positives),
            "plate_solve_rate": rate(len(solved_positives), len(positives)),
            "correct_top12": len(correct_positives),
            "end_to_end_success_rate": rate(len(correct_positives), len(positives)),
            "conditional_top12_rate": rate(len(correct_positives), len(solved_positives)),
        },
        "negative_pipeline": {
            "images": len(negatives),
            "false_positives": len(false_positive_negatives),
            "false_positive_rate": rate(len(false_positive_negatives), len(negatives)),
        },
        "failure_types": dict(failures),
        "by_category": group_stats(rows, lambda row: row.get("category") or "Unknown"),
        "by_resolution": group_stats(rows, resolution_bucket),
        "recommendations": [
            "Validation 분할에서만 scale 범위와 downsample/하늘 크롭 설정을 조정합니다.",
            "Timeout 이미지는 1차 빠른 검색 후 축소·크롭하여 2차 재시도합니다.",
            "최적 설정이 확정될 때까지 Test 분할은 다시 평가하지 않습니다.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    text_path = args.output.with_suffix(".txt")
    lines = [
        "51번 Plate Solving 실패 분석",
        f"처리: {len(rows)}장 / 총 소요: {report['runtime']['total_hours']}시간",
        f"별자리 Solve 성공률: {report['positive_pipeline']['plate_solve_rate']}%",
        f"전체 기준 최종 성공률: {report['positive_pipeline']['end_to_end_success_rate']}%",
        f"Negative 오검출률: {report['negative_pipeline']['false_positive_rate']}%",
        f"실패 유형: {dict(failures)}",
        "",
        "다음 단계: Validation 데이터로 검색 설정을 개선한 뒤 Test를 최종 재평가합니다.",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"json: {args.output.resolve()}")
    print(f"summary: {text_path.resolve()}")


if __name__ == "__main__":
    main()
