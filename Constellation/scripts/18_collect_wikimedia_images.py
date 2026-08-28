"""Collect licensed smartphone night-sky images from Wikimedia Commons."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import requests
from dotenv import load_dotenv
from PIL import Image


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "photo" / "WikimediaCommons"
DEFAULT_IMAGES = DEFAULT_ROOT / "images"
DEFAULT_CSV = DEFAULT_ROOT / "metadata" / "sources.csv"
API_URL = "https://commons.wikimedia.org/w/api.php"
DEFAULT_QUERIES = [
    "smartphone astrophotography",
    "mobile phone night sky",
    "iPhone night sky stars",
    "Google Pixel astrophotography",
    "Samsung Galaxy astrophotography",
    "Xiaomi night sky stars",
]
CSV_FIELDS = [
    "filename", "title", "file_page_url", "original_url", "author", "credit",
    "license", "license_url", "description", "camera_make", "camera_model",
    "date_taken", "gps_latitude", "gps_longitude", "width", "height", "mime",
    "sha1", "search_query", "download_status", "rejection_reason",
]
PHONE_MAKES = {
    "apple", "google", "samsung", "xiaomi", "huawei", "oneplus", "oppo",
    "vivo", "motorola", "lg", "nokia", "honor", "realme", "nothing",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: Any) -> str:
    if value is None:
        return ""
    parser = _TextExtractor()
    parser.feed(html.unescape(str(value)))
    return " ".join(" ".join(parser.parts).split())


def parse_args() -> argparse.Namespace:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query", action="append", dest="queries",
        help="Commons 검색어. 여러 번 지정 가능하며 생략하면 기본 검색어를 사용합니다.",
    )
    parser.add_argument("--limit", type=int, default=20, help="새로 다운로드할 최대 사진 수")
    parser.add_argument("--per-query", type=int, default=50, choices=range(1, 51))
    parser.add_argument("--min-long-edge", type=int, default=1920)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--include-sharealike", action="store_true")
    parser.add_argument("--allow-missing-camera", action="store_true")
    parser.add_argument("--index-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pause-seconds", type=float, default=0.5)
    parser.add_argument(
        "--user-agent",
        default=os.getenv(
            "WIKIMEDIA_USER_AGENT",
            "ConstellationResearch/1.0 (educational research; local collector)",
        ),
    )
    return parser.parse_args()


def metadata_map(items: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {str(item.get("name")): item.get("value") for item in items}


def ext_value(ext: dict[str, Any], name: str) -> str:
    entry = ext.get(name, {})
    return plain_text(entry.get("value", "") if isinstance(entry, dict) else entry)


def is_smartphone(make: str, model: str) -> bool:
    make_lower = make.strip().lower()
    model_lower = model.strip().lower()
    if make_lower == "sony":
        return "xperia" in model_lower
    if make_lower in PHONE_MAKES:
        return "iphone" in model_lower if make_lower == "apple" else bool(model_lower)
    return any(token in model_lower for token in ("iphone", "pixel", "galaxy", "xperia", "oneplus"))


def license_allowed(name: str, include_sharealike: bool) -> bool:
    normalized = name.upper().replace("PUBLIC DOMAIN MARK", "PUBLIC DOMAIN")
    if normalized == "CC0" or "PUBLIC DOMAIN" in normalized:
        return True
    if normalized.startswith("CC BY"):
        has_sa = "-SA" in normalized or "SHAREALIKE" in normalized
        has_nc = "-NC" in normalized or "NONCOMMERCIAL" in normalized
        has_nd = "-ND" in normalized or "NODERIV" in normalized
        return not has_nc and not has_nd and (include_sharealike or not has_sa)
    return False


def safe_filename(title: str, url: str) -> str:
    url_name = unquote(Path(urlparse(url).path).name)
    candidate = url_name or title.removeprefix("File:")
    candidate = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", candidate).strip(" .")
    return candidate or "wikimedia_image.jpg"


def result_row(page: dict[str, Any], query: str) -> dict[str, Any] | None:
    infos = page.get("imageinfo") or []
    if not infos:
        return None
    info = infos[0]
    meta = metadata_map(info.get("metadata", []))
    ext = info.get("extmetadata", {})
    url = str(info.get("url", ""))
    return {
        "filename": safe_filename(str(page.get("title", "")), url),
        "title": str(page.get("title", "")),
        "file_page_url": str(info.get("descriptionurl", "")),
        "original_url": url,
        "author": ext_value(ext, "Artist"),
        "credit": ext_value(ext, "Credit"),
        "license": ext_value(ext, "LicenseShortName") or ext_value(ext, "UsageTerms"),
        "license_url": ext_value(ext, "LicenseUrl"),
        "description": ext_value(ext, "ImageDescription"),
        "camera_make": plain_text(meta.get("Make", "")),
        "camera_model": plain_text(meta.get("Model", "")),
        "date_taken": plain_text(meta.get("DateTimeOriginal", "")) or ext_value(ext, "DateTimeOriginal"),
        "gps_latitude": plain_text(meta.get("GPSLatitude", "")),
        "gps_longitude": plain_text(meta.get("GPSLongitude", "")),
        "width": info.get("width", ""),
        "height": info.get("height", ""),
        "mime": str(info.get("mime", "")),
        "sha1": str(info.get("sha1", "")).lower(),
        "search_query": query,
        "download_status": "candidate",
        "rejection_reason": "",
    }


def classify(row: dict[str, Any], args: argparse.Namespace) -> str:
    reasons: list[str] = []
    if row["mime"] not in {"image/jpeg", "image/png", "image/webp"}:
        reasons.append("not_supported_image")
    if max(int(row["width"] or 0), int(row["height"] or 0)) < args.min_long_edge:
        reasons.append("resolution_too_small")
    if not license_allowed(str(row["license"]), args.include_sharealike):
        reasons.append("license_not_allowed")
    if not args.allow_missing_camera and not is_smartphone(
        str(row["camera_make"]), str(row["camera_model"])
    ):
        reasons.append("not_verified_smartphone")
    return "|".join(reasons)


def api_get(session: requests.Session, params: dict[str, Any]) -> dict[str, Any]:
    response = session.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"Wikimedia API 오류: {payload['error']}")
    return payload


def api_params() -> dict[str, Any]:
    return {
        "action": "query", "format": "json", "formatversion": 2,
        "prop": "imageinfo", "iiprop": "url|size|mime|sha1|metadata|extmetadata",
        "iiextmetadatafilter": (
            "Artist|Credit|LicenseShortName|LicenseUrl|UsageTerms|"
            "ImageDescription|DateTimeOriginal"
        ),
        "iiextmetadatalanguage": "en",
    }


def search_pages(session: requests.Session, query: str, per_query: int) -> list[dict[str, Any]]:
    params = api_params()
    params.update({
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": per_query, "gsrsort": "relevance",
    })
    return api_get(session, params).get("query", {}).get("pages", [])


def lookup_titles(session: requests.Session, titles: list[str]) -> list[dict[str, Any]]:
    if not titles:
        return []
    params = api_params()
    params["titles"] = "|".join(titles)
    return api_get(session, params).get("query", {}).get("pages", [])


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def download_image(session: requests.Session, row: dict[str, Any], images_dir: Path) -> Path:
    images_dir.mkdir(parents=True, exist_ok=True)
    destination = images_dir / str(row["filename"])
    if destination.exists():
        local_sha1 = hashlib.sha1(destination.read_bytes()).hexdigest()
        if not row["sha1"] or local_sha1 == row["sha1"]:
            return destination
        destination = destination.with_stem(f"{destination.stem}_{str(row['sha1'])[:8]}")
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha1()
    with session.get(str(row["original_url"]), stream=True, timeout=120) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    digest.update(chunk)
    if row["sha1"] and digest.hexdigest() != row["sha1"]:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-1 불일치: {row['title']}")
    with Image.open(temporary) as image:
        image.verify()
    temporary.replace(destination)
    return destination


def upsert_rows(current: list[dict[str, Any]], incoming: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    positions = {
        (str(row.get("sha1", "")), str(row.get("title", ""))): index
        for index, row in enumerate(current)
    }
    for row in incoming:
        key = (str(row.get("sha1", "")), str(row.get("title", "")))
        if key in positions:
            current[positions[key]].update(row)
        else:
            positions[key] = len(current)
            current.append(row)
    return current


def index_existing(session: requests.Session, images_dir: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    files = [path for path in images_dir.glob("*") if path.is_file()]
    titles = [f"File:{path.name.replace('_', ' ')}" for path in files]
    pages = lookup_titles(session, titles)
    rows: list[dict[str, Any]] = []
    local_by_normalized = {path.name.replace("_", " ").lower(): path for path in files}
    for page in pages:
        row = result_row(page, "existing_file")
        if not row:
            continue
        page_name = str(page.get("title", "")).removeprefix("File:").lower()
        local = local_by_normalized.get(page_name)
        if not local:
            continue
        row["filename"] = local.name
        row["download_status"] = "existing"
        row["rejection_reason"] = classify(row, args)
        rows.append(row)
    return rows


def main() -> None:
    args = parse_args()
    if args.limit < 0:
        raise ValueError("--limit은 0 이상이어야 합니다.")
    images_dir = args.images_dir.resolve()
    csv_path = args.csv.resolve()
    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent, "Accept": "application/json"})
    rows: list[dict[str, Any]] = read_rows(csv_path)
    known_sha1 = {
        str(row.get("sha1", ""))
        for row in rows
        if row.get("sha1") and row.get("download_status") in {"existing", "downloaded"}
    }
    seen_sha1 = set(known_sha1)

    if args.index_existing:
        existing_rows = index_existing(session, images_dir, args)
        rows = upsert_rows(rows, existing_rows)
        known_sha1.update(str(row.get("sha1", "")) for row in existing_rows)
        seen_sha1.update(known_sha1)
        print(f"기존 사진 메타데이터 등록: {len(existing_rows)}개")

    downloaded = 0
    rejected = 0
    queries = args.queries or DEFAULT_QUERIES
    if args.limit > 0:
        for query in queries:
            print(f"검색: {query}")
            for page in search_pages(session, query, args.per_query):
                row = result_row(page, query)
                if not row or row["sha1"] in seen_sha1:
                    continue
                seen_sha1.add(str(row["sha1"]))
                rejection = classify(row, args)
                if rejection:
                    rejected += 1
                    continue
                if args.dry_run:
                    row["download_status"] = "dry_run_candidate"
                    print(
                        f"  후보: {row['camera_make']} {row['camera_model']} / "
                        f"{row['license']} / {row['filename']}"
                    )
                else:
                    saved = download_image(session, row, images_dir)
                    row["filename"] = saved.name
                    row["download_status"] = "downloaded"
                    rows = upsert_rows(rows, [row])
                    known_sha1.add(str(row["sha1"]))
                downloaded += 1
                if not args.dry_run:
                    print(
                        f"  다운로드: {row['camera_make']} {row['camera_model']} / "
                        f"{row['license']} / {row['filename']}"
                    )
                if downloaded >= args.limit:
                    break
                time.sleep(max(args.pause_seconds, 0.0))
            if downloaded >= args.limit:
                break

    write_rows(csv_path, rows)
    print(f"신규 선택 사진: {downloaded}개")
    print(f"검색 제외 기록: {rejected}개")
    print(f"전체 메타데이터 행: {len(rows)}개")
    print(f"images: {images_dir}")
    print(f"sources_csv: {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("사용자에 의해 중단되었습니다.", file=sys.stderr)
        raise SystemExit(130)
