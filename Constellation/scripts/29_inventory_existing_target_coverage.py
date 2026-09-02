"""Inventory AstroSmartphoneDataset and build capture/session representatives.

This stage does not plate-solve or modify source images.  It extracts safe EXIF
fields, groups burst/processed variants into capture groups, groups captures into
observing sessions, detects exact duplicates, and creates the representative
queue consumed by stage 30.  GPS coordinates are never written to artifacts;
only their presence is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from PIL import ExifTags, Image

from lib.io_utils import configure_utf8_console, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "photo" / "AstroSmartphoneDataset"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_inventory"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
FILENAME_TIME = re.compile(r"PXL_(\d{8})_(\d{9})", re.IGNORECASE)
BURST_INDEX = re.compile(r"_(\d{4})(?:~\d+)?$")
EXIF_ID = {name: tag for tag, name in ExifTags.TAGS.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--capture-gap-seconds", type=float, default=5.0)
    parser.add_argument("--session-gap-minutes", type=float, default=30.0)
    parser.add_argument("--skip-sha256", action="store_true", help="Skip exact duplicate hashing")
    return parser.parse_args()


def discover_images(dataset: Path) -> list[Path]:
    if not dataset.is_dir():
        raise FileNotFoundError(f"AstroSmartphoneDataset을 찾을 수 없습니다: {dataset}")
    return sorted(
        path for path in dataset.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def folder_parts(path: Path, dataset: Path) -> tuple[str, str, str]:
    relative = path.relative_to(dataset)
    folder = relative.parts[0] if len(relative.parts) > 1 else path.parent.name
    if "-" in folder:
        device_folder, resolution_kind = folder.rsplit("-", 2)[0], "high" if "high-res" in folder else "medium"
    else:
        device_folder, resolution_kind = folder, "unknown"
    return folder, device_folder, resolution_kind


def filename_datetime(name: str) -> datetime | None:
    match = FILENAME_TIME.search(name)
    if not match:
        return None
    try:
        return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S%f")
    except ValueError:
        return None


def parse_exif_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    for pattern in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value).strip(), pattern)
        except ValueError:
            pass
    return None


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip("\x00 ")
    return str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def burst_index(path: Path) -> int | None:
    match = BURST_INDEX.search(path.stem)
    return int(match.group(1)) if match else None


def inspect_image(path: Path, dataset: Path, calculate_hash: bool) -> dict[str, Any]:
    folder, device_folder, resolution_kind = folder_parts(path, dataset)
    stat = path.stat()
    error = ""
    width = height = 0
    image_format = camera_make = camera_model = exif_datetime = ""
    gps_available = False
    try:
        with Image.open(path) as image:
            width, height = image.size
            image_format = text(image.format)
            exif = image.getexif()
            camera_make = text(exif.get(EXIF_ID.get("Make")))
            camera_model = text(exif.get(EXIF_ID.get("Model")))
            exif_datetime = text(
                exif.get(EXIF_ID.get("DateTimeOriginal"))
                or exif.get(EXIF_ID.get("DateTimeDigitized"))
                or exif.get(EXIF_ID.get("DateTime"))
            )
            gps_available = bool(exif.get(EXIF_ID.get("GPSInfo")))
            image.verify()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    filename_time = filename_datetime(path.name)
    exif_time = parse_exif_datetime(exif_datetime)
    captured = filename_time or exif_time
    return {
        "relative_path": path.relative_to(dataset).as_posix(),
        "source_path": str(path.resolve()),
        "folder": folder,
        "device_folder": device_folder,
        "resolution_kind": resolution_kind,
        "filename": path.name,
        "stem": path.stem,
        "extension": path.suffix.lower(),
        "file_size_bytes": stat.st_size,
        "width": width,
        "height": height,
        "megapixels": round(width * height / 1_000_000, 3),
        "image_format": image_format,
        "camera_make": camera_make,
        "camera_model": camera_model,
        "captured_at": captured.isoformat(timespec="milliseconds") if captured else "",
        "timestamp_source": "filename" if filename_time else ("exif" if exif_time else "missing"),
        "gps_available": gps_available,
        "burst_index": burst_index(path),
        "processed_variant": "~" in path.stem,
        "sha256": sha256_file(path) if calculate_hash and not error else "",
        "read_error": error,
        "capture_group_id": "",
        "session_id": "",
        "is_capture_representative": False,
        "is_session_representative": False,
        "duplicate_of": "",
    }


def datetime_from_row(row: dict[str, Any]) -> datetime | None:
    value = row.get("captured_at")
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def assign_capture_groups(rows: list[dict[str, Any]], gap_seconds: float) -> None:
    by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_device[row["device_folder"]].append(row)
    for device, device_rows in sorted(by_device.items()):
        timed = sorted(
            (row for row in device_rows if datetime_from_row(row) is not None),
            key=lambda row: (datetime_from_row(row), row["filename"]),
        )
        group_number = 0
        previous_time: datetime | None = None
        current_id = ""
        for row in timed:
            captured = datetime_from_row(row)
            assert captured is not None
            if previous_time is None or (captured - previous_time).total_seconds() > gap_seconds:
                group_number += 1
                current_id = f"C_{device}_{captured:%Y%m%dT%H%M%S}_{group_number:04d}"
            row["capture_group_id"] = current_id
            previous_time = captured
        for row in sorted((row for row in device_rows if not row["capture_group_id"]), key=lambda value: value["filename"]):
            group_number += 1
            row["capture_group_id"] = f"C_{device}_unknown_{group_number:04d}"


def assign_sessions(rows: list[dict[str, Any]], gap_minutes: float) -> None:
    captures: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        captures[row["capture_group_id"]].append(row)
    by_device: dict[str, list[tuple[str, datetime | None]]] = defaultdict(list)
    for capture_id, group in captures.items():
        times = [value for value in (datetime_from_row(row) for row in group) if value is not None]
        by_device[group[0]["device_folder"]].append((capture_id, min(times) if times else None))
    session_for_capture: dict[str, str] = {}
    for device, values in sorted(by_device.items()):
        values.sort(key=lambda item: (item[1] is None, item[1] or datetime.max, item[0]))
        session_number = 0
        previous: datetime | None = None
        current = ""
        for capture_id, captured in values:
            if captured is None or previous is None or captured - previous > timedelta(minutes=gap_minutes):
                session_number += 1
                suffix = captured.strftime("%Y%m%dT%H%M") if captured else "unknown"
                current = f"S_{device}_{suffix}_{session_number:03d}"
            session_for_capture[capture_id] = current
            if captured is not None:
                previous = captured
    for row in rows:
        row["session_id"] = session_for_capture[row["capture_group_id"]]


def mark_duplicates(rows: list[dict[str, Any]]) -> int:
    first_by_hash: dict[str, str] = {}
    count = 0
    for row in rows:
        digest = row.get("sha256", "")
        if not digest:
            continue
        if digest in first_by_hash:
            row["duplicate_of"] = first_by_hash[digest]
            count += 1
        else:
            first_by_hash[digest] = row["relative_path"]
    return count


def choose_capture_representatives(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["capture_group_id"]].append(row)
    representatives: list[dict[str, Any]] = []
    for capture_id, group in sorted(groups.items()):
        usable = [row for row in group if not row["read_error"] and not row["duplicate_of"]] or [row for row in group if not row["read_error"]]
        if not usable:
            continue
        indexes = [row["burst_index"] for row in usable if row["burst_index"] is not None]
        middle = float(median(indexes)) if indexes else 0.0
        def score(row: dict[str, Any]) -> tuple[Any, ...]:
            high_priority = 0 if row["resolution_kind"] == "high" else 1
            variant_penalty = 1 if row["processed_variant"] else 0
            index_distance = abs(float(row["burst_index"] or middle) - middle) if high_priority else 0.0
            pixels = int(row["width"]) * int(row["height"])
            return high_priority, variant_penalty, index_distance, -pixels, -int(row["file_size_bytes"]), row["filename"]
        selected = min(usable, key=score)
        selected["is_capture_representative"] = True
        representatives.append(selected)
    return representatives


def mark_session_representatives(representatives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in representatives:
        groups[row["session_id"]].append(row)
    selected_rows: list[dict[str, Any]] = []
    for _, group in sorted(groups.items()):
        selected = max(
            group,
            key=lambda row: (
                row["resolution_kind"] == "high",
                int(row["width"]) * int(row["height"]),
                int(row["file_size_bytes"]),
            ),
        )
        selected["is_session_representative"] = True
        selected_rows.append(selected)
    return selected_rows


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    dataset = args.dataset.resolve()
    output = args.output_dir.resolve()
    images = discover_images(dataset)
    if not images:
        raise RuntimeError(f"이미지가 없습니다: {dataset}")
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(images, 1):
        rows.append(inspect_image(path, dataset, not args.skip_sha256))
        if index % 250 == 0 or index == len(images):
            print(f"검사: {index:,}/{len(images):,}")

    assign_capture_groups(rows, args.capture_gap_seconds)
    assign_sessions(rows, args.session_gap_minutes)
    duplicate_count = mark_duplicates(rows)
    capture_representatives = choose_capture_representatives(rows)
    session_representatives = mark_session_representatives(capture_representatives)

    image_fields = [
        "relative_path", "source_path", "folder", "device_folder", "resolution_kind",
        "filename", "stem", "extension", "file_size_bytes", "width", "height", "megapixels",
        "image_format", "camera_make", "camera_model", "captured_at", "timestamp_source",
        "gps_available", "burst_index", "processed_variant", "sha256", "read_error",
        "capture_group_id", "session_id", "is_capture_representative",
        "is_session_representative", "duplicate_of",
    ]
    representative_fields = [
        "capture_group_id", "session_id", "source_path", "relative_path", "filename",
        "device_folder", "resolution_kind", "camera_make", "camera_model", "captured_at",
        "gps_available", "width", "height", "megapixels", "file_size_bytes",
        "is_session_representative",
    ]
    capture_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        capture_groups[row["capture_group_id"]].append(row)
        sessions[row["session_id"]].append(row)
    representative_by_capture = {row["capture_group_id"]: row for row in capture_representatives}
    capture_rows = []
    for capture_id, group in sorted(capture_groups.items()):
        representative = representative_by_capture.get(capture_id, {})
        capture_rows.append({
            "capture_group_id": capture_id, "session_id": group[0]["session_id"],
            "device_folder": group[0]["device_folder"], "image_count": len(group),
            "high_res_images": sum(row["resolution_kind"] == "high" for row in group),
            "medium_res_images": sum(row["resolution_kind"] == "medium" for row in group),
            "duplicate_images": sum(bool(row["duplicate_of"]) for row in group),
            "capture_started_at": min((row["captured_at"] for row in group if row["captured_at"]), default=""),
            "representative_path": representative.get("source_path", ""),
            "representative_filename": representative.get("filename", ""),
            "representative_resolution": representative.get("resolution_kind", ""),
        })
    session_rows = []
    session_representative_map = {row["session_id"]: row for row in session_representatives}
    for session_id, group in sorted(sessions.items()):
        session_capture_ids = {row["capture_group_id"] for row in group}
        representative = session_representative_map.get(session_id, {})
        times = sorted(row["captured_at"] for row in group if row["captured_at"])
        session_rows.append({
            "session_id": session_id, "device_folder": group[0]["device_folder"],
            "image_count": len(group), "capture_group_count": len(session_capture_ids),
            "started_at": times[0] if times else "", "ended_at": times[-1] if times else "",
            "gps_available_images": sum(bool(row["gps_available"]) for row in group),
            "representative_path": representative.get("source_path", ""),
            "representative_filename": representative.get("filename", ""),
        })
    device_rows = []
    for device in sorted({row["device_folder"] for row in rows}):
        selected = [row for row in rows if row["device_folder"] == device]
        device_rows.append({
            "device_folder": device, "images": len(selected),
            "capture_groups": len({row["capture_group_id"] for row in selected}),
            "sessions": len({row["session_id"] for row in selected}),
            "high_res_images": sum(row["resolution_kind"] == "high" for row in selected),
            "medium_res_images": sum(row["resolution_kind"] == "medium" for row in selected),
            "gps_available_images": sum(bool(row["gps_available"]) for row in selected),
            "camera_models": "|".join(sorted({row["camera_model"] for row in selected if row["camera_model"]})),
        })

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "image_inventory.csv", rows, image_fields)
    write_csv(output / "capture_group_manifest.csv", capture_rows, list(capture_rows[0].keys()))
    write_csv(output / "session_manifest.csv", session_rows, list(session_rows[0].keys()))
    write_csv(output / "representative_images.csv", capture_representatives, representative_fields)
    write_csv(output / "plate_solve_queue.csv", capture_representatives, representative_fields)
    write_csv(output / "session_representatives.csv", session_representatives, representative_fields)
    write_csv(output / "device_distribution.csv", device_rows, list(device_rows[0].keys()))
    write_csv(output / "session_distribution.csv", session_rows, list(session_rows[0].keys()))
    folder_counts = Counter(row["folder"] for row in rows)
    summary = {
        "dataset_path": str(dataset), "total_images": len(rows),
        "total_size_bytes": sum(int(row["file_size_bytes"]) for row in rows),
        "readable_images": sum(not row["read_error"] for row in rows),
        "corrupt_images": sum(bool(row["read_error"]) for row in rows),
        "capture_groups": len(capture_groups), "observing_sessions": len(sessions),
        "capture_representatives": len(capture_representatives),
        "session_representatives": len(session_representatives),
        "exact_duplicate_images": duplicate_count,
        "high_res_images": sum(row["resolution_kind"] == "high" for row in rows),
        "medium_res_images": sum(row["resolution_kind"] == "medium" for row in rows),
        "exif_camera_model_present": sum(bool(row["camera_model"]) for row in rows),
        "gps_available": sum(bool(row["gps_available"]) for row in rows),
        "capture_gap_seconds": args.capture_gap_seconds,
        "session_gap_minutes": args.session_gap_minutes,
        "folder_counts": dict(sorted(folder_counts.items())),
        "privacy": "GPS coordinates are not written; only gps_available is retained.",
        "source_images_modified": False,
        "next_stage": "30_batch_plate_solve_sessions.py using plate_solve_queue.csv",
    }
    write_json(output / "summary.json", summary)
    print("AstroSmartphoneDataset 인벤토리 완료")
    print(f"전체 이미지: {len(rows):,}장")
    print(f"촬영 묶음: {len(capture_groups):,}개")
    print(f"관측 세션: {len(sessions):,}개")
    print(f"Plate Solving 대표 사진: {len(capture_representatives):,}장")
    print(f"정확히 중복된 이미지: {duplicate_count:,}장")
    print(f"inventory: {output / 'image_inventory.csv'}")
    print(f"plate_solve_queue: {output / 'plate_solve_queue.csv'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
