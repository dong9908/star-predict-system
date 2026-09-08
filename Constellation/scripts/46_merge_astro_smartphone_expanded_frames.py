"""Merge stage-45 aligned AstroSmartphone frames into the latest YOLO dataset.

Only selected, successfully aligned frames are eligible.  They are added to
train only, while validation and test remain byte-for-byte sourced from the
base dataset.  SHA-256 duplicate detection prevents representative images that
already exist in the base dataset from being added again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_astro_targeted_8"
DEFAULT_STAGE45 = PROJECT_ROOT / "data" / "results" / "astro_smartphone_frame_expansion"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_astro_targeted_frames_8"
SPLITS = ("train", "validation", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dataset", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stage45-dir", type=Path, default=DEFAULT_STAGE45)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--link-mode", choices=("hardlink", "copy", "symlink"), default="hardlink")
    parser.add_argument("--accept-auto-selected", action="store_true", help="Treat pending selected rows as accepted")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def materialize(source: Path, target: Path, mode: str, replace: bool) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        try:
            if os.path.samefile(source, target):
                return "reused"
        except OSError:
            pass
        if not replace:
            if target.stat().st_size == source.stat().st_size:
                return "reused_existing"
            raise FileExistsError(f"대상 파일이 이미 존재합니다: {target}. --replace-existing을 사용하세요.")
        target.unlink()
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(source)
    else:
        shutil.copy2(source, target)
    return "created"


def classes_from_yaml(path: Path) -> list[str]:
    return [
        line.split(":", 1)[1].strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()[:1].isdigit() and ":" in line
    ]


def dataset_yaml(output: Path, classes: list[str]) -> str:
    lines = [
        f"path: {output.as_posix()}", "train: images/train", "val: images/validation",
        "test: images/test", f"nc: {len(classes)}", "names:",
    ]
    lines.extend(f"  {index}: {name}" for index, name in enumerate(classes))
    return "\n".join(lines) + "\n"


def parse_label(path: Path, class_count: int) -> Counter[int]:
    counts: Counter[int] = Counter()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 5:
            raise ValueError(f"YOLO 라벨 열 오류 {path}:{line_number}")
        try:
            class_id = int(parts[0])
            x, y, width, height = (float(value) for value in parts[1:])
        except ValueError as exc:
            raise ValueError(f"YOLO 라벨 숫자 오류 {path}:{line_number}") from exc
        if not 0 <= class_id < class_count:
            raise ValueError(f"YOLO 클래스 오류 {path}:{line_number}")
        if not all(0 <= value <= 1 for value in (x, y, width, height)) or width <= 0 or height <= 0:
            raise ValueError(f"YOLO 좌표 오류 {path}:{line_number}")
        counts[class_id] += 1
    if not counts:
        raise ValueError(f"확장 양성 라벨이 비어 있습니다: {path}")
    return counts


def images_for_split(base: Path, split: str) -> list[Path]:
    folder = base / "images" / split
    if not folder.is_dir():
        raise FileNotFoundError(f"기존 이미지 폴더가 없습니다: {folder}")
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    base, stage45, output = args.base_dataset.resolve(), args.stage45_dir.resolve(), args.output_dir.resolve()
    required = [base / "dataset.yaml", stage45 / "frame_review.csv", stage45 / "summary.json"]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"필수 입력이 없습니다: {path}")
    if output == base:
        raise ValueError("출력 데이터셋은 기존 데이터셋과 달라야 합니다.")

    stage_summary = json.loads((stage45 / "summary.json").read_text(encoding="utf-8"))
    review_rows = read_csv(stage45 / "frame_review.csv")
    selected_rows = [
        row for row in review_rows
        if truthy(row.get("selected"))
        and row.get("alignment_status") in {"reference", "aligned"}
        and (row.get("review_decision", "").strip().lower() == "accept" or (args.accept_auto_selected and row.get("review_decision", "").strip().lower() == "pending"))
    ]
    pending_selected = [row for row in review_rows if truthy(row.get("selected")) and row.get("review_decision", "").strip().lower() == "pending"]
    if pending_selected and not args.accept_auto_selected:
        raise RuntimeError(f"45번 선택 프레임 {len(pending_selected)}장이 아직 pending입니다. 검토하거나 --accept-auto-selected를 사용하세요.")
    if not selected_rows:
        raise RuntimeError("병합할 승인 프레임이 없습니다.")

    classes = classes_from_yaml(base / "dataset.yaml")
    if len(classes) != 8:
        raise ValueError(f"기존 dataset.yaml에서 8개 클래스를 읽지 못했습니다: {classes}")
    test_sessions = {
        row.get("session_id", "") for row in read_csv(PROJECT_ROOT / "data" / "results" / "astro_smartphone_target_coverage" / "image_target_coverage.csv")
        if row.get("split_candidate") == "test_candidate" and row.get("session_id")
    }
    overlap = sorted({row.get("session_id", "") for row in selected_rows if row.get("session_id") in test_sessions})
    if overlap:
        raise RuntimeError(f"독립 Test 세션이 확장 Train 후보에 포함됐습니다: {overlap[:5]}")

    base_index_path = base / "dataset_index.csv"
    base_index = {
        (row.get("split", ""), row.get("sample_id", "")): row
        for row in read_csv(base_index_path)
    } if base_index_path.is_file() else {}
    rows: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    links: Counter[str] = Counter()
    known_hashes: dict[str, str] = {}
    class_objects: Counter[tuple[str, int]] = Counter()
    class_images: Counter[tuple[str, int]] = Counter()
    source_counts: Counter[str] = Counter()

    def add_sample(sample_id: str, split: str, source_name: str, image: Path, label: Path, metadata: dict[str, Any]) -> dict[str, Any]:
        counts = parse_label(label, len(classes)) if label.read_text(encoding="utf-8-sig").strip() else Counter()
        image_target = output / "images" / split / f"{sample_id}{image.suffix.lower()}"
        label_target = output / "labels" / split / f"{sample_id}.txt"
        links[materialize(image, image_target, args.link_mode, args.replace_existing)] += 1
        links[materialize(label, label_target, args.link_mode, args.replace_existing)] += 1
        for class_id, count in counts.items():
            class_objects[(split, class_id)] += count
            class_images[(split, class_id)] += 1
        source_counts[source_name] += 1
        result = {
            "sample_id": sample_id, "split": split, "dataset_source": source_name,
            "session_id": metadata.get("session_id", ""), "capture_group_id": metadata.get("capture_group_id", ""),
            "image_path": str(image_target), "label_path": str(label_target),
            "source_image": str(image), "source_label": str(label),
            "object_count": sum(counts.values()), "class_ids": "|".join(str(value) for value in sorted(counts)),
            "background": not bool(counts), "sha256": sha256(image),
            "alignment_response": metadata.get("alignment_response", ""),
            "shift_x_norm": metadata.get("shift_x_norm", ""), "shift_y_norm": metadata.get("shift_y_norm", ""),
            "source_page_url": metadata.get("source_page_url", ""), "license": metadata.get("license", ""),
            "creator": metadata.get("creator", ""), "link_mode": args.link_mode,
        }
        rows.append(result)
        return result

    print("기존 최신 데이터셋을 연결하고 중복 해시를 계산하는 중...")
    for split in SPLITS:
        for image in images_for_split(base, split):
            label = base / "labels" / split / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"기존 라벨이 없습니다: {label}")
            digest = sha256(image)
            known_hashes.setdefault(digest, f"{split}/{image.name}")
            old = base_index.get((split, image.stem), {})
            add_sample(image.stem, split, old.get("dataset_source", "base_existing"), image, label, old)

    for candidate in selected_rows:
        image = Path(candidate["source_path"])
        label = Path(candidate["generated_label_path"])
        if not image.is_file() or not label.is_file():
            raise FileNotFoundError(f"45번 선택 파일이 없습니다: {candidate['sample_id']}")
        digest = sha256(image)
        if digest in known_hashes:
            duplicates.append({
                "sample_id": candidate["sample_id"], "source_image": str(image),
                "duplicate_of": known_hashes[digest], "sha256": digest,
            })
            continue
        result = add_sample(candidate["sample_id"], "train", "astro_smartphone_expanded_frame", image, label, candidate)
        known_hashes[digest] = f"train/{candidate['sample_id']}{image.suffix.lower()}"
        added.append(result)

    output.mkdir(parents=True, exist_ok=True)
    (output / "dataset.yaml").write_text(dataset_yaml(output, classes), encoding="utf-8")
    write_csv(output / "dataset_index.csv", rows, list(rows[0].keys()))
    write_csv(output / "astro_frames_added.csv", added, list(rows[0].keys()))
    write_csv(output / "astro_frames_duplicates_skipped.csv", duplicates, ["sample_id", "source_image", "duplicate_of", "sha256"])
    distribution = []
    for split in SPLITS:
        for class_id, class_name in enumerate(classes):
            distribution.append({
                "split": split, "class_id": class_id, "class_name": class_name,
                "objects": class_objects[(split, class_id)], "images_with_class": class_images[(split, class_id)],
            })
    write_csv(output / "class_distribution.csv", distribution, list(distribution[0].keys()))
    split_counts = Counter(row["split"] for row in rows)
    added_classes: Counter[int] = Counter()
    for row in added:
        added_classes.update(parse_label(Path(row["label_path"]), len(classes)))
    summary = {
        "status": "completed", "output_dataset": str(output), "base_dataset": str(base),
        "classes": classes, "split_counts": dict(split_counts), "source_counts": dict(source_counts),
        "stage45_selected": int(stage_summary.get("selected_frames", 0)), "eligible_selected": len(selected_rows),
        "expanded_frames_added": len(added), "exact_duplicates_skipped": len(duplicates),
        "expanded_objects_by_class": {classes[index]: added_classes[index] for index in range(len(classes))},
        "expanded_split": "train_only", "validation_unchanged": True, "test_unchanged": True,
        "test_session_overlap": 0, "pending_auto_accepted": bool(args.accept_auto_selected and pending_selected),
        "exact_duplicate_check": "sha256_across_all_splits", "link_mode": args.link_mode,
        "link_status": dict(links), "source_images_modified": False,
    }
    write_json(output / "summary.json", summary)
    print("46번 AstroSmartphone 확장 프레임 YOLO 병합 완료")
    print(f"45번 선택: {len(selected_rows)}장 / 신규 추가: {len(added)}장 / 정확 중복 제외: {len(duplicates)}장")
    print(f"전체 Train/Validation/Test: {split_counts['train']}/{split_counts['validation']}/{split_counts['test']}")
    print("Validation/Test 변경: 없음 / Test 세션 누수: 0")
    print(f"dataset: {output / 'dataset.yaml'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
