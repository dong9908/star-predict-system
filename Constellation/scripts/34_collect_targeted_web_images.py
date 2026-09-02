"""Collect targeted, reusable night-sky images from four public providers.

Providers:
* Wikimedia Commons: searches file pages and downloads licensed thumbnails.
* Openverse: searches openly licensed images and downloads provider thumbnails.
* Zenodo: searches research records; downloads only standalone image files.
* Hugging Face: searches datasets; downloads only small standalone image files.

Large archives are deliberately never downloaded.  They are written to
``dataset_candidates.csv`` for manual licence and content review.  Every image
row preserves its source page, creator and licence and is de-duplicated by
SHA-256 after download.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, unquote, urlparse

import requests
from dotenv import load_dotenv
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "photo" / "TargetedWeb"
PROVIDERS = ("wikimedia", "openverse", "zenodo", "huggingface")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
DIRECT_LICENSES = {"cc0", "pdm", "by", "by-sa"}
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024

QUERY_GROUPS = {
    "hassaleh": [
        "Hassaleh night sky", "Iota Aurigae night sky",
        "Auriga smartphone astrophotography", "Auriga mobile phone stars",
    ],
    "bellatrix": [
        "Bellatrix night sky", "Orion smartphone astrophotography",
        "Orion mobile phone night sky",
    ],
    "aldebaran": [
        "Aldebaran night sky", "Taurus smartphone astrophotography",
        "Taurus mobile phone night sky",
    ],
    "zeta_tauri": [
        "Zeta Tauri night sky", "Taurus constellation smartphone photo",
    ],
    "other_targets": [
        "Pleiades smartphone astrophotography", "Jupiter smartphone night sky",
        "Betelgeuse smartphone photo", "Elnath night sky smartphone",
    ],
    "negative": [
        "smartphone starry sky", "mobile phone night sky stars",
        "iPhone night sky stars", "Google Pixel astrophotography",
        "Samsung Galaxy astrophotography", "smartphone cloudy night sky",
        "smartphone night sky light pollution",
    ],
    "seasonal": [
        "winter constellation smartphone", "summer constellation smartphone",
        "spring night sky smartphone", "autumn night sky smartphone",
    ],
}

SOURCE_FIELDS = [
    "local_filename", "provider", "provider_id", "query_group", "search_query",
    "title", "creator", "license", "license_url", "source_page_url",
    "download_url", "width", "height", "mime", "camera_make", "camera_model",
    "device_status", "sha256", "bytes", "download_status", "rejection_reason",
    "collected_at_utc",
]
CANDIDATE_FIELDS = [
    "provider", "provider_id", "search_query", "title", "description",
    "license", "license_url", "source_page_url", "download_url", "file_name",
    "file_size", "candidate_reason", "collected_at_utc",
]


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", action="append", choices=PROVIDERS,
        help="수집처(반복 지정 가능). 생략하면 네 곳 모두 사용합니다.",
    )
    parser.add_argument(
        "--group", action="append", choices=tuple(QUERY_GROUPS),
        help="검색 그룹(반복 지정 가능). 생략하면 모든 그룹을 사용합니다.",
    )
    parser.add_argument(
        "--query", action="append", default=[],
        help="추가 검색어. 지정한 검색어는 custom 그룹으로 기록합니다.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--limit-per-provider", type=int, default=30)
    parser.add_argument("--results-per-query", type=int, default=20)
    parser.add_argument("--max-download-mb", type=float, default=25.0)
    parser.add_argument("--thumbnail-width", type=int, default=1600)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--allow-unknown-license", action="store_true")
    parser.add_argument(
        "--user-agent",
        default=os.getenv(
            "WIKIMEDIA_USER_AGENT",
            "ConstellationResearch/1.0 (educational research; contact required)",
        ),
    )
    return parser.parse_args()


def clean_html(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", unescape(str(value or "")))
    return " ".join(text.split())


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def merge_rows(
    current: list[dict[str, Any]], incoming: Iterable[dict[str, Any]], keys: tuple[str, ...]
) -> list[dict[str, Any]]:
    positions = {tuple(str(row.get(key, "")) for key in keys): i for i, row in enumerate(current)}
    for row in incoming:
        identity = tuple(str(row.get(key, "")) for key in keys)
        if identity in positions:
            current[positions[identity]].update(row)
        else:
            positions[identity] = len(current)
            current.append(row)
    return current


def request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    retries: int = 5,
    **kwargs: Any,
) -> requests.Response:
    delay = 2.0
    for attempt in range(retries):
        try:
            response = session.request(method, url, timeout=(20, 120), **kwargs)
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
        except (requests.Timeout, requests.ConnectionError):
            if attempt == retries - 1:
                raise
            wait = delay
        if attempt == retries - 1:
            response.raise_for_status()
        time.sleep(min(wait, 60.0))
        delay *= 2
    raise RuntimeError("HTTP 재시도 횟수를 초과했습니다.")


def safe_name(provider: str, provider_id: str, url: str, title: str) -> str:
    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        suffix = ".jpg"
    stem = re.sub(r"[^0-9A-Za-z._-]+", "_", str(provider_id)).strip("._")[:80]
    if not stem:
        stem = hashlib.sha1(f"{provider}|{url}|{title}".encode()).hexdigest()[:20]
    return f"{provider}_{stem}{suffix}"


def license_is_allowed(license_name: str, license_url: str, allow_unknown: bool) -> bool:
    value = f"{license_name} {license_url}".lower().replace("_", "-")
    short_name = license_name.strip().lower().replace("_", "-")
    if not value.strip():
        return allow_unknown
    if any(bad in value for bad in ("-nc", "noncommercial", "-nd", "noderivatives")):
        return False
    return (
        short_name in DIRECT_LICENSES
        or any(good in value for good in (
            "cc0", "public domain", "pdm", "cc by", "cc-by", "by-sa",
            "creativecommons.org/licenses/by/",
        ))
    )


def device_status(make: str, model: str, text: str) -> str:
    value = f"{make} {model} {text}".lower()
    phone_terms = (
        "smartphone", "mobile phone", "iphone", "google pixel", "pixel phone",
        "samsung galaxy", "oneplus", "xiaomi", "huawei", "oppo", "vivo",
        "motorola", "xperia", "night sight",
    )
    professional = ("canon eos", "nikon d", "sony ilce", "fujifilm", "telescope")
    if any(term in value for term in phone_terms):
        return "smartphone_probable"
    if any(term in value for term in professional):
        return "professional_or_telescope"
    return "device_unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_image(
    session: requests.Session,
    row: dict[str, Any],
    images_dir: Path,
    known_hashes: set[str],
    max_bytes: int,
) -> dict[str, Any]:
    url = str(row.get("download_url", ""))
    if not url:
        row["download_status"] = "metadata_only"
        row["rejection_reason"] = "missing_download_url"
        return row
    images_dir.mkdir(parents=True, exist_ok=True)
    destination = images_dir / safe_name(
        str(row["provider"]), str(row["provider_id"]), url, str(row["title"])
    )
    if destination.is_file():
        digest = sha256_file(destination)
        row.update({
            "local_filename": destination.name, "sha256": digest,
            "bytes": destination.stat().st_size, "download_status": "existing",
        })
        known_hashes.add(digest)
        return row
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with request(session, "GET", url, stream=True) as response:
            declared = int(response.headers.get("Content-Length", 0) or 0)
            if declared and declared > max_bytes:
                row.update(download_status="skipped", rejection_reason="file_too_large")
                return row
            digest = hashlib.sha256()
            total = 0
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("file_too_large")
                    handle.write(chunk)
                    digest.update(chunk)
        with Image.open(temporary) as image:
            image.verify()
        hash_value = digest.hexdigest()
        if hash_value in known_hashes:
            temporary.unlink(missing_ok=True)
            row.update(download_status="duplicate", rejection_reason="sha256_duplicate", sha256=hash_value)
            return row
        temporary.replace(destination)
        known_hashes.add(hash_value)
        row.update({
            "local_filename": destination.name, "sha256": hash_value,
            "bytes": total, "download_status": "downloaded",
        })
    except Exception as error:
        temporary.unlink(missing_ok=True)
        row["download_status"] = "failed" if str(error) != "file_too_large" else "skipped"
        row["rejection_reason"] = str(error)[:240]
    return row


def ext_value(ext: dict[str, Any], name: str) -> str:
    value = ext.get(name, {})
    return clean_html(value.get("value", "") if isinstance(value, dict) else value)


def collect_wikimedia(
    session: requests.Session, query: str, group: str, args: argparse.Namespace
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    response = request(session, "GET", "https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": min(args.results_per_query, 50),
        "prop": "imageinfo", "iiprop": "url|size|mime|sha1|metadata|extmetadata",
        "iiurlwidth": args.thumbnail_width,
        "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|UsageTerms|ImageDescription",
        "iiextmetadatalanguage": "en",
    }).json()
    rows: list[dict[str, Any]] = []
    for page in response.get("query", {}).get("pages", []):
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        ext = info.get("extmetadata", {})
        metadata = {str(x.get("name")): clean_html(x.get("value")) for x in info.get("metadata", [])}
        license_name = ext_value(ext, "LicenseShortName") or ext_value(ext, "UsageTerms")
        license_url = ext_value(ext, "LicenseUrl")
        download_url = str(info.get("thumburl") or info.get("url") or "")
        title = str(page.get("title", ""))
        make, model = metadata.get("Make", ""), metadata.get("Model", "")
        rows.append({
            "provider": "wikimedia", "provider_id": str(page.get("pageid", "")),
            "query_group": group, "search_query": query, "title": title,
            "creator": ext_value(ext, "Artist"), "license": license_name,
            "license_url": license_url, "source_page_url": str(info.get("descriptionurl", "")),
            "download_url": download_url, "width": info.get("thumbwidth") or info.get("width", ""),
            "height": info.get("thumbheight") or info.get("height", ""),
            "mime": info.get("mime", ""), "camera_make": make, "camera_model": model,
            "device_status": device_status(make, model, f"{title} {ext_value(ext, 'ImageDescription')}"),
            "download_status": "candidate", "rejection_reason": "", "collected_at_utc": now_utc(),
        })
    return rows, []


def openverse_token(session: requests.Session) -> str:
    configured = os.getenv("OPENVERSE_ACCESS_TOKEN", "").strip()
    if configured:
        return configured
    client_id = os.getenv("OPENVERSE_CLIENT_ID", "").strip()
    client_secret = os.getenv("OPENVERSE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return ""
    response = request(session, "POST", "https://api.openverse.org/v1/auth_tokens/token/", data={
        "client_id": client_id, "client_secret": client_secret,
        "grant_type": "client_credentials",
    })
    return str(response.json().get("access_token", ""))


def collect_openverse(
    session: requests.Session, query: str, group: str, args: argparse.Namespace, token: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = request(session, "GET", "https://api.openverse.org/v1/images/", headers=headers, params={
        "q": query, "page_size": min(args.results_per_query, 50),
        "license": "cc0,pdm,by,by-sa",
    }).json()
    rows = []
    for item in payload.get("results", []):
        license_name = str(item.get("license", ""))
        license_url = str(item.get("license_url", ""))
        title = str(item.get("title", ""))
        detail = " ".join(str(item.get(key, "")) for key in ("tags", "attribution", "source"))
        rows.append({
            "provider": "openverse", "provider_id": str(item.get("id", "")),
            "query_group": group, "search_query": query, "title": title,
            "creator": str(item.get("creator", "")), "license": license_name,
            "license_url": license_url, "source_page_url": str(item.get("foreign_landing_url", "")),
            "download_url": str(item.get("thumbnail") or item.get("url") or ""),
            "width": item.get("width", ""), "height": item.get("height", ""),
            "mime": mimetypes.guess_type(str(item.get("url", "")))[0] or "",
            "camera_make": "", "camera_model": "",
            "device_status": device_status("", "", f"{title} {detail}"),
            "download_status": "candidate", "rejection_reason": "", "collected_at_utc": now_utc(),
        })
    return rows, []


def collect_zenodo(
    session: requests.Session, query: str, group: str, args: argparse.Namespace
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = request(session, "GET", "https://zenodo.org/api/records", params={
        "q": query, "size": min(args.results_per_query, 25), "sort": "bestmatch",
    }).json()
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for record in payload.get("hits", {}).get("hits", []):
        metadata = record.get("metadata", {})
        record_id = str(record.get("id", ""))
        title = clean_html(metadata.get("title", ""))
        license_data = metadata.get("license") or {}
        license_name = str(license_data.get("id", "") if isinstance(license_data, dict) else license_data)
        creators = ", ".join(str(x.get("name", "")) for x in metadata.get("creators", []))
        source_page = str(record.get("links", {}).get("html", f"https://zenodo.org/records/{record_id}"))
        description = clean_html(metadata.get("description", ""))
        files = record.get("files", [])
        for file_info in files:
            file_name = str(file_info.get("key") or "")
            suffix = Path(file_name).suffix.lower()
            size = int(file_info.get("size") or 0)
            links = file_info.get("links", {})
            download_url = str(links.get("content") or links.get("self") or "")
            if suffix in IMAGE_SUFFIXES and size <= int(args.max_download_mb * 1024 * 1024):
                rows.append({
                    "provider": "zenodo", "provider_id": f"{record_id}:{file_name}",
                    "query_group": group, "search_query": query, "title": f"{title} / {file_name}",
                    "creator": creators, "license": license_name, "license_url": "",
                    "source_page_url": source_page, "download_url": download_url,
                    "width": "", "height": "", "mime": mimetypes.guess_type(file_name)[0] or "",
                    "camera_make": "", "camera_model": "",
                    "device_status": device_status("", "", f"{title} {description}"),
                    "download_status": "candidate", "rejection_reason": "", "collected_at_utc": now_utc(),
                })
            else:
                candidates.append({
                    "provider": "zenodo", "provider_id": record_id, "search_query": query,
                    "title": title, "description": description, "license": license_name,
                    "license_url": "", "source_page_url": source_page, "download_url": download_url,
                    "file_name": file_name, "file_size": size,
                    "candidate_reason": "archive_or_large_non_image", "collected_at_utc": now_utc(),
                })
        if not files:
            candidates.append({
                "provider": "zenodo", "provider_id": record_id, "search_query": query,
                "title": title, "description": description, "license": license_name,
                "license_url": "", "source_page_url": source_page, "download_url": "",
                "file_name": "", "file_size": "", "candidate_reason": "record_without_files",
                "collected_at_utc": now_utc(),
            })
    return rows, candidates


def collect_huggingface(
    session: requests.Session, query: str, group: str, args: argparse.Namespace
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headers: dict[str, str] = {}
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    datasets = request(session, "GET", "https://huggingface.co/api/datasets", headers=headers, params={
        "search": query, "limit": min(args.results_per_query, 20), "full": "true",
    }).json()
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for dataset in datasets:
        dataset_id = str(dataset.get("id") or dataset.get("modelId") or "")
        if not dataset_id:
            continue
        card = dataset.get("cardData") or {}
        license_value = card.get("license", "") if isinstance(card, dict) else ""
        if isinstance(license_value, list):
            license_name = ",".join(str(x) for x in license_value)
        else:
            license_name = str(license_value)
        source_page = f"https://huggingface.co/datasets/{dataset_id}"
        siblings = dataset.get("siblings") or []
        image_siblings = [x for x in siblings if Path(str(x.get("rfilename", ""))).suffix.lower() in IMAGE_SUFFIXES]
        for sibling in image_siblings[: args.results_per_query]:
            file_name = str(sibling.get("rfilename", ""))
            download_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{quote(file_name, safe='/')}"
            rows.append({
                "provider": "huggingface", "provider_id": f"{dataset_id}:{file_name}",
                "query_group": group, "search_query": query, "title": f"{dataset_id} / {file_name}",
                "creator": str(dataset.get("author", "")), "license": license_name,
                "license_url": "", "source_page_url": source_page, "download_url": download_url,
                "width": "", "height": "", "mime": mimetypes.guess_type(file_name)[0] or "",
                "camera_make": "", "camera_model": "",
                "device_status": device_status("", "", f"{dataset_id} {file_name}"),
                "download_status": "candidate", "rejection_reason": "", "collected_at_utc": now_utc(),
            })
        candidates.append({
            "provider": "huggingface", "provider_id": dataset_id, "search_query": query,
            "title": dataset_id, "description": " ".join(str(x) for x in dataset.get("tags", [])),
            "license": license_name, "license_url": "", "source_page_url": source_page,
            "download_url": "", "file_name": "", "file_size": "",
            "candidate_reason": "dataset_requires_manual_review", "collected_at_utc": now_utc(),
        })
    return rows, candidates


def query_plan(args: argparse.Namespace) -> list[tuple[str, str]]:
    # Explicit queries alone are useful for a quick test and must not also run
    # the entire built-in query catalogue.
    groups = args.group or ([] if args.query else list(QUERY_GROUPS))
    plan = [(group, query) for group in groups for query in QUERY_GROUPS[group]]
    plan.extend(("custom", query) for query in args.query)
    return plan


def main() -> None:
    configure_console()
    args = parse_args()
    if args.limit_per_provider < 0 or args.results_per_query < 1:
        raise ValueError("수집 제한값을 확인하세요.")
    args.max_download_mb = max(0.1, args.max_download_mb)
    output_root = args.output_root.resolve()
    images_dir = output_root / "images"
    metadata_dir = output_root / "metadata"
    sources_path = metadata_dir / "sources.csv"
    candidates_path = metadata_dir / "dataset_candidates.csv"
    summary_path = metadata_dir / "collection_summary.json"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    sources: list[dict[str, Any]] = read_csv(sources_path)
    candidates: list[dict[str, Any]] = read_csv(candidates_path)
    known_hashes = {str(row.get("sha256", "")) for row in sources if row.get("sha256")}
    for image_path in images_dir.glob("*") if images_dir.is_dir() else []:
        if image_path.is_file():
            known_hashes.add(sha256_file(image_path))

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent, "Accept": "application/json"})
    providers = args.provider or list(PROVIDERS)
    plan = query_plan(args)
    provider_counts: dict[str, dict[str, int]] = {}
    openverse_access_token = ""
    if "openverse" in providers:
        try:
            openverse_access_token = openverse_token(session)
        except Exception as error:
            print(f"주의: Openverse 토큰 발급 실패: {error}")

    collectors = {
        "wikimedia": lambda q, g: collect_wikimedia(session, q, g, args),
        "openverse": lambda q, g: collect_openverse(session, q, g, args, openverse_access_token),
        "zenodo": lambda q, g: collect_zenodo(session, q, g, args),
        "huggingface": lambda q, g: collect_huggingface(session, q, g, args),
    }

    for provider in providers:
        selected = downloaded = failed = skipped = 0
        provider_error = ""
        print(f"\n[{provider}] 수집 시작")
        for group, query in plan:
            if selected >= args.limit_per_provider:
                break
            print(f"  검색({group}): {query}")
            try:
                found, found_candidates = collectors[provider](query, group)
            except requests.HTTPError as error:
                print(f"    검색 실패: HTTP {error.response.status_code} - {error}")
                if provider == "openverse" and error.response.status_code == 401:
                    provider_error = "authentication_required"
                    print("    Openverse 인증이 없어 이 공급처를 중단합니다. 다른 공급처는 계속 진행합니다.")
                    print("    .env에 OPENVERSE_CLIENT_ID/OPENVERSE_CLIENT_SECRET을 설정한 뒤 다시 실행하세요.")
                    break
                if error.response.status_code == 429:
                    provider_error = "rate_limited"
                continue
            except Exception as error:
                print(f"    검색 실패: {type(error).__name__}: {error}")
                continue
            candidates = merge_rows(candidates, found_candidates, ("provider", "provider_id", "file_name"))
            for row in found:
                if selected >= args.limit_per_provider:
                    break
                if not license_is_allowed(str(row.get("license", "")), str(row.get("license_url", "")), args.allow_unknown_license):
                    row.update(download_status="skipped", rejection_reason="license_not_allowed_or_unknown")
                    sources = merge_rows(sources, [row], ("provider", "provider_id"))
                    skipped += 1
                    continue
                selected += 1
                if args.metadata_only:
                    row["download_status"] = "metadata_only"
                else:
                    row = download_image(
                        session, row, images_dir, known_hashes,
                        min(int(args.max_download_mb * 1024 * 1024), MAX_DOWNLOAD_BYTES),
                    )
                    if row["download_status"] in {"downloaded", "existing"}:
                        downloaded += 1
                        print(f"    저장: {row.get('local_filename', '')}")
                    elif row["download_status"] == "failed":
                        failed += 1
                    else:
                        skipped += 1
                sources = merge_rows(sources, [row], ("provider", "provider_id"))
                write_csv(sources_path, sources, SOURCE_FIELDS)
                write_csv(candidates_path, candidates, CANDIDATE_FIELDS)
                time.sleep(max(args.pause_seconds, 0.0))
        provider_counts[provider] = {
            "selected": selected, "downloaded_or_existing": downloaded,
            "failed": failed, "skipped": skipped, "provider_error": provider_error,
        }

    write_csv(sources_path, sources, SOURCE_FIELDS)
    write_csv(candidates_path, candidates, CANDIDATE_FIELDS)
    summary = {
        "status": "completed", "completed_at_utc": now_utc(),
        "providers": providers, "query_count": len(plan),
        "metadata_only": args.metadata_only, "provider_counts": provider_counts,
        "source_rows": len(sources), "dataset_candidate_rows": len(candidates),
        "downloaded_files": len([x for x in images_dir.glob("*") if x.is_file()]) if images_dir.is_dir() else 0,
        "paths": {
            "images": str(images_dir), "sources_csv": str(sources_path),
            "dataset_candidates_csv": str(candidates_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n통합 웹 수집 완료")
    print(f"이미지 파일: {summary['downloaded_files']}개")
    print(f"메타데이터: {len(sources)}행")
    print(f"대형 데이터셋 후보: {len(candidates)}행")
    print(f"images: {images_dir}")
    print(f"sources: {sources_path}")
    print(f"candidates: {candidates_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("사용자에 의해 중단되었습니다. 저장된 CSV부터 이어서 실행할 수 있습니다.", file=sys.stderr)
        raise SystemExit(130)
