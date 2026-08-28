"""Diagnose evaluation errors and separate model failures from label-set conflicts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "results" / "ground_truth_evaluation" / "evaluation_results.csv"
DEFAULT_TRUTH = PROJECT_ROOT / "data" / "evaluation" / "verified_smartphone" / "ground_truth.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "error_analysis"
STAR_ROOT = PROJECT_ROOT / "data" / "results" / "star_detection"
VALIDATION_ROOT = PROJECT_ROOT / "data" / "results" / "match_validation"
OVERLAY_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"
WCS_ROOT = PROJECT_ROOT / "data" / "wcs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def labels(value: str | None) -> set[str]:
    return {part.strip().upper() for part in re.split(r"[|;,]", value or "") if part.strip()}


def boolean(value: str | None) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_evidence(stem: str) -> dict[str, Any]:
    stars = load_json(STAR_ROOT / stem / f"{stem}_stars.json")
    validation = load_json(VALIDATION_ROOT / stem / f"{stem}_validation.json")
    overlay = load_json(OVERLAY_ROOT / stem / f"{stem}_wcs_constellations.json")
    plate = load_json(WCS_ROOT / stem / f"{stem}_plate_solve.json")
    selected = overlay.get("selected", [])
    return {
        "detected_stars": stars.get("detected_stars"),
        "star_limit_reached": stars.get("maximum_star_limit_reached"),
        "component_candidates": stars.get("component_candidates_before_ranking"),
        "plate_status": plate.get("status"),
        "plate_error": plate.get("error"),
        "plate_elapsed_seconds": plate.get("elapsed_seconds"),
        "global_wcs_status": validation.get("wcs_validation", {}).get("global_reprojection", {}).get("status"),
        "overlay_status": overlay.get("decision", {}).get("status"),
        "overlay_selected": "|".join(str(item.get("iau")) for item in selected if item.get("iau")),
        "minimum_selected_score": min((float(item.get("score", 0)) for item in selected), default=None),
        "minimum_selected_matched_stars": min((int(item.get("matched_stars", 0)) for item in selected), default=None),
    }


def diagnose(result: dict[str, str], truth: dict[str, str]) -> tuple[str, str, str]:
    expected = labels(result.get("expected_iau"))
    predicted = labels(result.get("predicted_iau"))
    positive = boolean(result.get("should_recognize"))
    recognized = boolean(result.get("recognized"))
    inherited = truth.get("verification") == "same_night_sight_burst_as_verified_anchor"
    if not positive:
        if recognized and inherited:
            return (
                "ground_truth_negative_inheritance_conflict",
                "dataset",
                "대표 사진의 Plate Solving 실패를 동일 촬영 프레임의 인식 불가 정답으로 상속할 수 없습니다.",
            )
        if recognized:
            return "possible_false_positive", "recognition", "음성 대표 사진에서 별자리를 확정했습니다. 수동 검토가 필요합니다."
        return "correct_rejection", "none", "인식 실패 정답을 올바르게 거부했습니다."
    if not recognized:
        failure = result.get("failure_code") or "unrecognized"
        owner = "plate_solving" if failure == "plate_solve_failed" else "recognition"
        return f"positive_{failure}", owner, "양성 사진을 확정하지 못했습니다."
    missing = expected - predicted
    extra = predicted - expected
    if not missing and not extra:
        return "exact_match", "none", "정답 집합과 완전히 일치합니다."
    if not missing and extra:
        return (
            "extra_labels_beyond_verified_set",
            "dataset_or_threshold",
            "모든 검증 라벨을 찾았고 추가 별자리도 검출했습니다. 정답이 비포괄적이므로 오검출로 단정할 수 없습니다.",
        )
    if missing and not extra:
        return "missing_verified_labels", "overlay", "검증된 별자리 일부를 누락했습니다."
    return "mixed_missing_and_extra", "overlay_or_dataset", "검증 라벨 누락과 추가 검출이 함께 있습니다."


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 6) if b else None


def main() -> None:
    args = parse_args()
    results = load_csv(args.results.resolve())
    truth_rows = load_csv(args.ground_truth.resolve())
    truth = {row["stem"]: row for row in truth_rows}
    analyzed: list[dict[str, Any]] = []
    for row in results:
        category, owner, explanation = diagnose(row, truth.get(row["stem"], {}))
        expected = labels(row.get("expected_iau"))
        predicted = labels(row.get("predicted_iau"))
        analyzed.append(
            {
                "stem": row["stem"],
                "scene_id": row["scene_id"],
                "evaluation_type": row["evaluation_type"],
                "expected_iau": row.get("expected_iau"),
                "predicted_iau": row.get("predicted_iau"),
                "missing_labels": "|".join(sorted(expected - predicted)),
                "extra_labels": "|".join(sorted(predicted - expected)),
                "category": category,
                "owner": owner,
                "explanation": explanation,
                **artifact_evidence(row["stem"]),
            }
        )

    positive = [row for row in analyzed if row["evaluation_type"] == "positive"]
    inherited_negative = [
        row for row in analyzed if row["category"] == "ground_truth_negative_inheritance_conflict"
    ]
    all_expected_found = sum(not row["missing_labels"] for row in positive)
    any_expected_found = sum(
        bool(labels(row["expected_iau"]) & labels(row["predicted_iau"])) for row in positive
    )
    categories = dict(sorted(Counter(row["category"] for row in analyzed).items()))
    owners = dict(sorted(Counter(row["owner"] for row in analyzed if row["owner"] != "none").items()))
    recommendations: list[dict[str, Any]] = []
    if inherited_negative:
        recommendations.append(
            {
                "target": "12_build_ground_truth_evaluation.py",
                "action": "Plate Solving 실패 라벨을 같은 burst의 다른 프레임에 음성으로 상속하지 않습니다.",
                "evidence": f"음성 상속 충돌 {len(inherited_negative)}건",
            }
        )
    if categories.get("positive_plate_solve_failed", 0):
        recommendations.append(
            {
                "target": "07_plate_solving.py",
                "action": "Nova 연결 오류 재시도 또는 동일 burst WCS 초기값 활용을 적용합니다.",
                "evidence": f"양성 Plate Solving 실패 {categories['positive_plate_solve_failed']}건",
            }
        )
    recommendations.extend(
        [
            {
                "target": "ground_truth_enrichment",
                "action": "WCS 사진 경계와 IAU 경계를 교차해 시야 내 별자리를 포괄적으로 라벨링한 뒤 extra-label 정확도를 재평가합니다.",
                "evidence": f"현재 라벨은 verified-present 방식이며 추가 라벨 사례 {categories.get('extra_labels_beyond_verified_set', 0)}건",
            },
            {
                "target": "evaluation_dataset",
                "action": "독립 장면을 현재 9개에서 최소 30개 이상으로 늘려 장면 편향을 줄입니다.",
                "evidence": "50장은 연속 burst 프레임을 포함하므로 독립 장면은 9개입니다.",
            },
        ]
    )
    for priority, recommendation in enumerate(recommendations, start=1):
        recommendation["priority"] = priority
    metrics = {
        "samples": len(analyzed),
        "positive_samples": len(positive),
        "all_expected_labels_found_rate": ratio(all_expected_found, len(positive)),
        "any_expected_label_found_rate": ratio(any_expected_found, len(positive)),
        "negative_inheritance_conflicts": len(inherited_negative),
        "categories": categories,
        "owners": owners,
    }
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "error_analysis.csv", analyzed)
    write_csv(output / "recommended_actions.csv", recommendations)
    (output / "error_analysis.json").write_text(
        json.dumps({"metrics": metrics, "recommendations": recommendations, "rows": analyzed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# 별자리 평가 오류 분석",
        "",
        f"- 분석 사진: {len(analyzed)}장",
        f"- 양성에서 모든 검증 라벨 발견: {all_expected_found}/{len(positive)} ({ratio(all_expected_found, len(positive)):.2%})",
        f"- 양성에서 하나 이상 검증 라벨 발견: {any_expected_found}/{len(positive)} ({ratio(any_expected_found, len(positive)):.2%})",
        f"- 잘못 상속된 음성 라벨 충돌: {len(inherited_negative)}건",
        "",
        "## 오류 유형",
        "",
        *[f"- {key}: {value}건" for key, value in categories.items()],
        "",
        "## 우선 개선",
        "",
        *[f"{item['priority']}. {item['action']} ({item['evidence']})" for item in recommendations],
        "",
    ]
    (output / "error_analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"분석 완료: {len(analyzed)}장")
    print(f"모든 검증 라벨 발견: {all_expected_found}/{len(positive)}")
    print(f"하나 이상 검증 라벨 발견: {any_expected_found}/{len(positive)}")
    print(f"음성 라벨 상속 충돌: {len(inherited_negative)}")
    print(f"summary: {output / 'error_analysis_summary.md'}")
    print(f"analysis_csv: {output / 'error_analysis.csv'}")


if __name__ == "__main__":
    main()
