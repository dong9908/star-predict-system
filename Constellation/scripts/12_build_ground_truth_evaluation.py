"""Build a verified evaluation manifest from the local smartphone dataset."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "data" / "photo" / "AstroSmartphoneDataset"
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "10_end_to_end_pipeline.py"
PIPELINE_ROOT = PROJECT_ROOT / "data" / "results" / "pipeline"
VALIDATION_ROOT = PROJECT_ROOT / "data" / "results" / "match_validation"
OVERLAY_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"
WCS_ROOT = PROJECT_ROOT / "data" / "wcs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "verified_smartphone"
DATE_PATTERN = re.compile(r"PXL_(\d{8})_")
TIMESTAMP_PATTERN = re.compile(r"PXL_(\d{8})_(\d{9})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-positive", type=int, default=47)
    parser.add_argument("--target-negative", type=int, default=3)
    parser.add_argument("--target-positive-scenes", type=int, default=6)
    parser.add_argument("--target-negative-scenes", type=int, default=3)
    parser.add_argument("--frames-per-positive-scene", type=int, default=15)
    parser.add_argument("--frames-per-negative-scene", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=80)
    parser.add_argument("--max-per-device", type=int, default=20)
    parser.add_argument("--max-per-date", type=int, default=2)
    parser.add_argument("--candidate-resolution", choices=("medium", "high", "both"), default="medium")
    parser.add_argument("--sky-fraction", type=float, default=1.0)
    parser.add_argument("--plate-backend", choices=("auto", "local", "nova"), default="nova")
    parser.add_argument("--plate-timeout-seconds", type=int, default=300)
    parser.add_argument("--scale-lower", type=float, default=40.0)
    parser.add_argument("--scale-upper", type=float, default=110.0)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--select-only", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def image_stats(path: Path) -> tuple[float, float]:
    with Image.open(path) as image:
        gray = image.convert("L")
        gray.thumbnail((320, 320))
        values = np.asarray(gray, dtype=np.float32)
    return round(float(np.mean(values)), 4), round(float(np.std(values)), 4)


def capture_date(path: Path) -> str:
    match = DATE_PATTERN.search(path.name)
    return match.group(1) if match else "unknown"


def diverse_candidates(
    dataset_root: Path,
    maximum_per_device: int,
    maximum_per_date: int,
    candidate_resolution: str,
) -> list[dict[str, Any]]:
    devices: dict[str, list[Path]] = {}
    folder_patterns = {
        "medium": ("*-medium-res",),
        "high": ("*-high-res",),
        "both": ("*-medium-res", "*-high-res"),
    }[candidate_resolution]
    folders = [folder for pattern in folder_patterns for folder in dataset_root.resolve().glob(pattern)]
    for folder in sorted(folders):
        files = sorted(
            path for path in folder.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        if folder.name.endswith("-medium-res"):
            # One independently verified anchor per exact Night Sight burst.
            grouped: dict[str, list[Path]] = defaultdict(list)
            for path in files:
                grouped[re.sub(r"_\d{4}$", "", path.stem)].append(path)
            files = [sorted(paths)[0] for paths in grouped.values()]
        by_date: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            by_date[capture_date(path)].append(path)
        selected: list[Path] = []
        for occurrence in range(maximum_per_date):
            for date in sorted(by_date):
                if occurrence < len(by_date[date]):
                    selected.append(by_date[date][occurrence])
                    if len(selected) >= maximum_per_device:
                        break
            if len(selected) >= maximum_per_device:
                break
        devices[folder.name] = selected

    rows_by_device: dict[str, list[dict[str, Any]]] = {}
    for device, paths in devices.items():
        rows = []
        for path in paths:
            mean, std = image_stats(path)
            rows.append(
                {
                    "stem": path.stem,
                    "source_path": str(path.resolve()),
                    "device_folder": device,
                    "capture_date": capture_date(path),
                    "brightness_mean": mean,
                    "brightness_std": std,
                    "difficulty_hint": "difficult" if mean > 75 or mean < 8 or std < 12 else "normal",
                    "source_kind": "medium_burst_anchor" if "-medium-res" in device else "high_res_anchor",
                }
            )
        # Prefer dark, contrast-rich images for positive anchors while retaining difficult cases.
        normal = [row for row in rows if row["difficulty_hint"] == "normal"]
        difficult = [row for row in rows if row["difficulty_hint"] == "difficult"]
        normal.sort(key=lambda row: (abs(float(row["brightness_mean"]) - 30.0), -float(row["brightness_std"])))
        difficult.sort(key=lambda row: (-float(row["brightness_std"]), float(row["brightness_mean"])))
        mixed: list[dict[str, Any]] = []
        while normal or difficult:
            mixed.extend(normal[:3])
            del normal[:3]
            if difficult:
                mixed.append(difficult.pop(0))
        rows_by_device[device] = mixed

    result: list[dict[str, Any]] = []
    index = 0
    while any(index < len(rows) for rows in rows_by_device.values()):
        for device in sorted(rows_by_device):
            if index < len(rows_by_device[device]):
                result.append(rows_by_device[device][index])
        index += 1
    # Output folders are stem-based, so prevent accidental collision across devices.
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in result:
        if row["stem"] not in seen:
            unique.append(row)
            seen.add(row["stem"])
    return unique


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nova_supported_constellations(plate_report: dict[str, Any], selected: list[dict[str, Any]]) -> list[str]:
    objects = " ".join(str(value) for value in plate_report.get("objects_in_field", [])).lower()
    supported = []
    for item in selected:
        iau = str(item.get("iau") or "")
        native = str(item.get("native_name") or "")
        if native.lower() in objects or f"({iau.lower()})" in objects:
            supported.append(iau)
    return supported


def classify_result(candidate: dict[str, Any]) -> dict[str, Any]:
    stem = candidate["stem"]
    pipeline_path = PIPELINE_ROOT / stem / f"{stem}_pipeline.json"
    validation_path = VALIDATION_ROOT / stem / f"{stem}_validation.json"
    overlay_path = OVERLAY_ROOT / stem / f"{stem}_wcs_constellations.json"
    plate_path = WCS_ROOT / stem / f"{stem}_plate_solve.json"
    base = {
        **candidate,
        "pipeline_json": str(pipeline_path) if pipeline_path.is_file() else None,
        "validation_json": str(validation_path) if validation_path.is_file() else None,
        "overlay_json": str(overlay_path) if overlay_path.is_file() else None,
        "plate_report": str(plate_path) if plate_path.is_file() else None,
        "evaluation_type": "excluded",
        "expected_iau": "",
        "should_recognize": "",
        "verification": "not_verified",
        "failure_code": "pipeline_error",
        "notes": "필수 결과 파일이 없습니다.",
    }
    if not pipeline_path.is_file():
        return base
    pipeline = load_json(pipeline_path)
    outcome = pipeline.get("outcome", {})
    failure_code = outcome.get("failure_code")
    base["failure_code"] = failure_code
    if all(path.is_file() for path in (validation_path, overlay_path, plate_path)):
        validation = load_json(validation_path)
        overlay = load_json(overlay_path)
        plate = load_json(plate_path)
        global_status = (
            validation.get("wcs_validation", {})
            .get("global_reprojection", {})
            .get("status")
        )
        selected = overlay.get("selected", [])
        supported = nova_supported_constellations(plate, selected)
        if (
            plate.get("status") == "success"
            and global_status == "pass"
            and overlay.get("decision", {}).get("status") == "recognized"
            and supported
        ):
            base.update(
                {
                    "evaluation_type": "positive",
                    "expected_iau": "|".join(supported),
                    "should_recognize": "true",
                    "verification": "wcs_gaia_stellarium_nova_agreement",
                    "failure_code": "",
                    "notes": "WCS, Gaia 전역 재투영, Stellarium 연결선, Nova 필드 객체가 교차 일치함.",
                }
            )
            return base
    if failure_code in {"too_few_stars", "cloudy", "plate_solve_failed", "no_candidate"}:
        base.update(
            {
                "evaluation_type": "negative",
                "expected_iau": "",
                "should_recognize": "false",
                "verification": "pipeline_failure_verified",
                "notes": f"인식 불가 조건: {failure_code}",
            }
        )
    else:
        base["notes"] = f"자동 정답 기준 미충족: {failure_code or outcome.get('status')}"
    return base


def run_pipeline(path: Path, args: argparse.Namespace, log_path: Path) -> tuple[bool, str]:
    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        str(path),
        "--plate-backend",
        args.plate_backend,
        "--sky-fraction",
        str(args.sky_fraction),
        "--plate-timeout-seconds",
        str(args.plate_timeout_seconds),
        "--scale-units",
        "degwidth",
        "--scale-lower",
        str(args.scale_lower),
        "--scale-upper",
        str(args.scale_upper),
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output + ("\n" if output else ""), encoding="utf-8")
    if args.verbose and output:
        print(output)
    return completed.returncode == 0, output


def image_timestamp(path: Path) -> datetime | None:
    match = TIMESTAMP_PATTERN.search(path.name)
    if not match:
        return None
    return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S%f")


def evenly_spaced(items: list[Path], limit: int) -> list[Path]:
    if len(items) <= limit:
        return items
    indexes = np.linspace(0, len(items) - 1, limit, dtype=int)
    return [items[int(index)] for index in indexes]


def related_burst_frames(anchor: dict[str, Any], limit: int) -> list[Path]:
    """Return the anchor and frames from the nearest Night Sight burst."""
    anchor_path = Path(anchor["source_path"])
    result = [anchor_path]
    timestamp = image_timestamp(anchor_path)
    if timestamp is None or limit <= 1:
        return result
    medium_folder = anchor_path.parent.parent / anchor_path.parent.name.replace("-high-res", "-medium-res")
    if not medium_folder.is_dir():
        return result
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in medium_folder.glob("PXL_*.*"):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        groups[re.sub(r"_\d{4}$", "", path.stem)].append(path)
    nearest: tuple[float, list[Path]] | None = None
    for paths in groups.values():
        group_time = image_timestamp(paths[0])
        if group_time is None:
            continue
        distance = abs((group_time - timestamp).total_seconds())
        if nearest is None or distance < nearest[0]:
            nearest = (distance, sorted(paths))
    # High-res output and medium burst normally differ by less than two seconds.
    if nearest is not None and nearest[0] <= 5.0:
        siblings = [path for path in nearest[1] if path.resolve() != anchor_path.resolve()]
        result.extend(evenly_spaced(siblings, limit - 1))
    return result


def expand_verified_scenes(
    anchors: list[dict[str, Any]], args: argparse.Namespace
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for anchor in anchors:
        positive = anchor["evaluation_type"] == "positive"
        limit = args.frames_per_positive_scene if positive else args.frames_per_negative_scene
        for index, path in enumerate(related_burst_frames(anchor, limit)):
            inherited = index > 0
            rows.append(
                {
                    "sample_id": f"{anchor['stem']}__{index:02d}",
                    "stem": path.stem,
                    "scene_id": anchor["stem"],
                    "frame_role": "burst_frame" if inherited else "verified_anchor",
                    "source_path": str(path.resolve()),
                    "expected_iau": anchor["expected_iau"],
                    "should_recognize": anchor["should_recognize"],
                    "evaluation_type": anchor["evaluation_type"],
                    "evaluation_scope": "recognition" if positive else "failure_rejection",
                    "label_semantics": (
                        "verified_present_not_exhaustive" if positive else "verified_pipeline_failure_anchor"
                    ),
                    "device_folder": anchor["device_folder"].replace("-high-res", ""),
                    "capture_date": anchor["capture_date"],
                    "verification": (
                        "same_night_sight_burst_as_verified_anchor" if inherited else anchor["verification"]
                    ),
                    "label_source_stem": anchor["stem"],
                    "failure_code": anchor["failure_code"],
                    "pipeline_json": anchor["pipeline_json"] if not inherited else "",
                    "validation_json": anchor["validation_json"] if not inherited else "",
                    "overlay_json": anchor["overlay_json"] if not inherited else "",
                    "plate_report": anchor["plate_report"] if not inherited else "",
                    "notes": (
                        "대표 고해상도 사진과 5초 이내 동일 Night Sight 연속 촬영 묶음에서 정답을 상속함."
                        if inherited else anchor["notes"]
                    ),
                }
            )
    return rows


def balanced_scene_take(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Round-robin samples across scenes so one burst cannot dominate the set."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["scene_id"]].append(row)
    selected: list[dict[str, Any]] = []
    index = 0
    while len(selected) < limit:
        added = False
        for scene_id in sorted(groups):
            if index < len(groups[scene_id]):
                selected.append(groups[scene_id][index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        index += 1
    return selected


def main() -> None:
    args = parse_args()
    if args.target_positive < 1 or args.target_negative < 0:
        raise ValueError("목표 양성/음성 개수를 확인해주세요.")
    if args.max_attempts < args.target_positive_scenes + args.target_negative_scenes:
        raise ValueError("max-attempts는 목표 독립 장면 수 이상이어야 합니다.")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = diverse_candidates(
        args.dataset_root.resolve(), args.max_per_device, args.max_per_date,
        args.candidate_resolution,
    )[: args.max_attempts]
    candidate_fields = [
        "stem", "source_path", "device_folder", "capture_date", "brightness_mean",
        "brightness_std", "difficulty_hint", "source_kind",
    ]
    write_rows(output_dir / "candidate_manifest.csv", candidates, candidate_fields)
    print(f"선별 후보: {len(candidates)}장")
    if args.select_only:
        print(f"candidate_manifest: {output_dir / 'candidate_manifest.csv'}")
        return

    results_by_stem: dict[str, dict[str, Any]] = {}
    state_path = output_dir / "build_state.json"
    if state_path.is_file():
        state = load_json(state_path)
        results_by_stem = {row["stem"]: row for row in state.get("results", [])}

    for index, candidate in enumerate(candidates, start=1):
        positives = sum(row.get("evaluation_type") == "positive" for row in results_by_stem.values())
        negatives = sum(row.get("evaluation_type") == "negative" for row in results_by_stem.values())
        if positives >= args.target_positive_scenes and negatives >= args.target_negative_scenes:
            break
        stem = candidate["stem"]
        if stem in results_by_stem and results_by_stem[stem].get("evaluation_type") in {"positive", "negative"}:
            continue
        print(
            f"[{index}/{len(candidates)}] {candidate['device_folder']} / {stem} "
            f"(현재 positive={positives}, negative={negatives})"
        )
        succeeded, output = run_pipeline(
            Path(candidate["source_path"]), args, output_dir / "logs" / f"{stem}.log"
        )
        result = classify_result(candidate)
        if not succeeded and result["evaluation_type"] == "excluded":
            result["notes"] = "파이프라인 실패: " + output[-500:].replace("\n", " | ")
        results_by_stem[stem] = result
        print(
            f"  결과={result['evaluation_type']}, "
            f"정답={result['expected_iau'] or '-'}, 실패={result['failure_code'] or '-'}"
        )
        state_path.write_text(
            json.dumps({"results": list(results_by_stem.values())}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if args.pause_seconds > 0:
            time.sleep(args.pause_seconds)

    all_results = list(results_by_stem.values())
    positive_anchors = [row for row in all_results if row["evaluation_type"] == "positive"][: args.target_positive_scenes]
    negative_anchors = [row for row in all_results if row["evaluation_type"] == "negative"][: args.target_negative_scenes]
    anchors = positive_anchors + negative_anchors
    anchors.sort(key=lambda row: (row["evaluation_type"], row["device_folder"], row["capture_date"], row["stem"]))
    anchor_fields = [
        "stem", "expected_iau", "should_recognize", "evaluation_type", "source_path",
        "device_folder", "capture_date", "verification", "failure_code", "pipeline_json",
        "validation_json", "overlay_json", "plate_report", "notes",
    ]
    write_rows(output_dir / "anchor_ground_truth.csv", anchors, anchor_fields)
    expanded = expand_verified_scenes(anchors, args)
    positives = balanced_scene_take(
        [row for row in expanded if row["evaluation_type"] == "positive"], args.target_positive
    )
    negatives = balanced_scene_take(
        [row for row in expanded if row["evaluation_type"] == "negative"], args.target_negative
    )
    accepted = positives + negatives
    ground_truth_fields = [
        "sample_id", "stem", "scene_id", "frame_role", "source_path", "expected_iau", "should_recognize",
        "evaluation_type", "evaluation_scope", "label_semantics", "device_folder", "capture_date", "verification", "label_source_stem", "failure_code", "pipeline_json",
        "validation_json", "overlay_json", "plate_report", "notes",
    ]
    write_rows(output_dir / "ground_truth.csv", accepted, ground_truth_fields)
    all_attempt_fields = list(dict.fromkeys(key for row in all_results for key in row)) if all_results else candidate_fields
    write_rows(output_dir / "all_attempts.csv", all_results, all_attempt_fields)
    summary = {
        "target_positive": args.target_positive,
        "target_negative": args.target_negative,
        "accepted_positive": len(positives),
        "accepted_negative": len(negatives),
        "accepted_total": len(accepted),
        "verified_positive_scenes": len(positive_anchors),
        "verified_negative_scenes": len(negative_anchors),
        "attempted": len(all_results),
        "excluded": sum(row.get("evaluation_type") == "excluded" for row in all_results),
        "complete": (
            len(positive_anchors) >= args.target_positive_scenes
            and len(negative_anchors) >= args.target_negative_scenes
            and len(positives) >= args.target_positive
            and len(negatives) >= args.target_negative
        ),
        "split_rule": "Train/test 분할은 sample_id가 아니라 scene_id 단위로 수행해야 데이터 누출을 막을 수 있습니다.",
        "label_semantics_note": "양성 expected_iau는 존재가 검증된 별자리이며 시야의 모든 별자리를 완전히 열거한 라벨은 아닙니다. 음성은 대표 사진 자체의 파이프라인 실패 재현용입니다.",
        "license_note": "Source images remain under data/photo/AstroSmartphoneDataset CC BY-NC-ND 4.0; this manifest does not copy or modify them.",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"평가셋 생성 결과: positive={len(positives)}, negative={len(negatives)}, "
        f"total={len(accepted)}, complete={summary['complete']}"
    )
    print(f"ground_truth: {output_dir / 'ground_truth.csv'}")
    print(f"summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
