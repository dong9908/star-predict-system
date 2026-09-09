"""YOLO inference service for the constellation upload screen."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import hashlib
import csv
import threading
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = (
    PROJECT_ROOT
    / "Constellation"
    / "data"
    / "results"
    / "yolo_training"
    / "mobiltelesco_openverse_astro_targeted_frames8_yolo11n"
    / "weights"
    / "best.pt"
)
PORTABLE_RESULT_ROOT = Path(__file__).resolve().parents[1] / "assets" / "constellation_results"
REALTIME_PLATE_SOLVER = PROJECT_ROOT / "Constellation" / "scripts" / "48_realtime_plate_solve.py"
REALTIME_PLATE_ROOT = (
    PROJECT_ROOT / "Constellation" / "data" / "results" / "realtime_plate_solving"
)
_PLATE_SOLVE_LOCK = threading.Lock()

OBJECT_TO_GROUP = {
    "Pleiades": ("Taurus", "황소자리", "constellation"),
    "Aldebaran": ("Taurus", "황소자리", "constellation"),
    "Zeta Tauri": ("Taurus", "황소자리", "constellation"),
    "Elnath": ("Taurus", "황소자리", "constellation"),
    "Betelgeuse": ("Orion", "오리온자리", "constellation"),
    "Bellatrix": ("Orion", "오리온자리", "constellation"),
    "Hassaleh": ("Auriga", "마차부자리", "constellation"),
    "Jupiter": ("Jupiter", "목성", "planet"),
}

HYG_CATALOG = PROJECT_ROOT / "Constellation" / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv"


def find_known_wcs(content: bytes, filename: str) -> Path | None:
    """Return a cached WCS only when filename and bytes match a solved source."""
    results_path = (
        PROJECT_ROOT / "Constellation" / "data" / "results"
        / "astro_smartphone_plate_solving" / "plate_solve_results.csv"
    )
    if not filename or not results_path.is_file():
        return None
    uploaded_hash = hashlib.sha256(content).digest()
    with results_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("filename") != filename or row.get("status") not in {"success", "cached_success"}:
                continue
            source, wcs = Path(row.get("source_path", "")), Path(row.get("wcs_path", ""))
            if not source.is_file() or not wcs.is_file() or source.stat().st_size != len(content):
                continue
            if hashlib.sha256(source.read_bytes()).digest() == uploaded_hash:
                return wcs
    return None


def find_portable_result(content: bytes) -> dict | None:
    """Load a bundled deterministic result using only the uploaded bytes."""
    digest = hashlib.sha256(content).hexdigest().lower()
    result_path = PORTABLE_RESULT_ROOT / f"{digest}.json"
    if not result_path.is_file():
        return None
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["model"] = "portable-sha256-cache"
    payload["matchedBy"] = "sha256"
    payload.setdefault("plateSolving", {
        "status": "success" if payload.get("wcsVerified") else "unavailable",
        "cached": True,
        "aiUsed": False,
        "source": "portable-sha256-cache",
    })
    return payload


def _read_realtime_plate_result(result_path: Path, was_cached: bool) -> tuple[dict, Path | None]:
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "cached": was_cached,
            "message": "Plate Solving 결과를 읽지 못했습니다.",
        }, None

    artifact = str(result.get("artifacts", {}).get("wcs") or "")
    wcs_path = Path(artifact) if artifact else None
    if wcs_path is not None and not wcs_path.is_absolute():
        wcs_path = REALTIME_PLATE_ROOT / wcs_path
    if result.get("status") != "success" or wcs_path is None or not wcs_path.is_file():
        failure = result.get("failure") or {}
        return {
            "status": "failed",
            "cached": was_cached,
            "imageSha256": result.get("image_sha256"),
            "elapsedSeconds": result.get("elapsed_seconds"),
            "backend": result.get("backend"),
            "aiUsed": False,
            "errorType": failure.get("error_type"),
            "message": failure.get("message") or "Plate Solving으로 좌표를 확정하지 못했습니다.",
        }, None
    return {
        "status": "success",
        "cached": was_cached,
        "imageSha256": result.get("image_sha256"),
        "elapsedSeconds": result.get("elapsed_seconds"),
        "backend": result.get("backend"),
        "aiUsed": False,
        "solution": result.get("solution") or {},
        "message": "WCS 천구 좌표를 확인했습니다.",
    }, wcs_path


def run_realtime_plate_solving(content: bytes, suffix: str) -> tuple[dict, Path | None]:
    """Resolve an upload with stage 48, reusing its filename-independent SHA cache."""
    image_hash = hashlib.sha256(content).hexdigest().lower()
    result_path = REALTIME_PLATE_ROOT / image_hash / "result.json"
    with _PLATE_SOLVE_LOCK:
        if result_path.is_file():
            return _read_realtime_plate_result(result_path, was_cached=True)
        if not REALTIME_PLATE_SOLVER.is_file():
            return {
                "status": "unavailable",
                "cached": False,
                "imageSha256": image_hash,
                "aiUsed": False,
                "message": "48번 Plate Solving 스크립트가 없습니다.",
            }, None

        timeout_seconds = max(30, int(os.getenv("PLATE_SOLVE_TIMEOUT_SECONDS", "90")))
        scale_lower = float(os.getenv("PLATE_SOLVE_SCALE_LOWER", "20"))
        scale_upper = float(os.getenv("PLATE_SOLVE_SCALE_UPPER", "120"))
        distribution = os.getenv("PLATE_SOLVE_WSL_DISTRIBUTION", "Ubuntu")
        with tempfile.TemporaryDirectory(prefix="astra_plate_upload_") as temporary:
            image_path = Path(temporary) / f"{image_hash}{suffix}"
            image_path.write_bytes(content)
            command = [
                sys.executable, str(REALTIME_PLATE_SOLVER), str(image_path),
                "--output-dir", str(REALTIME_PLATE_ROOT),
                "--timeout-seconds", str(timeout_seconds),
                "--scale-lower", str(scale_lower), "--scale-upper", str(scale_upper),
                "--wsl-distribution", distribution,
            ]
            try:
                completed = subprocess.run(
                    command, cwd=PROJECT_ROOT / "Constellation", capture_output=True,
                    text=True, encoding="utf-8", errors="replace",
                    timeout=timeout_seconds + 45, check=False,
                )
            except subprocess.TimeoutExpired:
                return {
                    "status": "failed",
                    "cached": False,
                    "imageSha256": image_hash,
                    "aiUsed": False,
                    "errorType": "TimeoutError",
                    "message": f"Plate Solving이 {timeout_seconds + 45}초를 초과했습니다.",
                }, None
        if result_path.is_file():
            return _read_realtime_plate_result(result_path, was_cached=False)
        return {
            "status": "unavailable",
            "cached": False,
            "imageSha256": image_hash,
            "aiUsed": False,
            "errorType": "PlateSolverProcessError",
            "message": (completed.stderr.strip() or completed.stdout.strip())[-1000:],
        }, None


def overlay_from_selected(selected: list[dict], verified: bool) -> list[dict]:
    overlays = []
    for rank, candidate in enumerate(selected[:4], 1):
        matches = {int(hip): value for hip, value in (candidate.get("matches") or {}).items()}
        edges = []
        for line in candidate.get("lines", []):
            numeric = [int(value) for value in line if isinstance(value, (int, float))]
            for first, second in zip(numeric, numeric[1:]):
                if first in matches and second in matches:
                    edges.append({"from": first, "to": second})
        points = [
            {
                "id": hip,
                "x": round(float(value["detected_x"]), 2),
                "y": round(float(value["detected_y"]), 2),
                "error": round(float(value["error_px"]), 2),
            }
            for hip, value in matches.items()
        ]
        iau = str(candidate.get("iau") or "")
        native = str(candidate.get("native_name") or iau)
        overlays.append({
            "rank": rank,
            "status": "verified" if verified else "candidate",
            "candidate": native,
            "name": native,
            "iau": iau,
            "score": round(float(candidate.get("score") or 0), 1),
            "confidence": candidate.get("confidence", "high" if verified else "medium"),
            "verified": verified,
            "points": points,
            "edges": edges,
        })
    return overlays


def run_wcs_overlay(content: bytes, suffix: str, wcs_path: Path) -> list[dict]:
    scripts = PROJECT_ROOT / "Constellation" / "scripts"
    with tempfile.TemporaryDirectory(prefix="astra_wcs_") as temporary:
        root = Path(temporary)
        image_path = root / f"upload{suffix}"
        image_path.write_bytes(content)
        detection_root, overlay_root = root / "detection", root / "overlay"
        detection = detection_root / "upload" / "upload_stars.json"
        commands = [
            [sys.executable, str(scripts / "03_star_detection.py"), str(image_path),
             "--output-dir", str(detection_root), "--sky-fraction", "1.0", "--max-stars", "250"],
            [sys.executable, str(scripts / "11_wcs_constellation_overlay.py"), str(image_path),
             "--wcs", str(wcs_path), "--star-detection", str(detection),
             "--output-dir", str(overlay_root), "--max-constellations", "4"],
        ]
        try:
            for command in commands:
                completed = subprocess.run(
                    command, cwd=PROJECT_ROOT / "Constellation", capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30, check=False,
                )
                if completed.returncode != 0:
                    return []
        except subprocess.TimeoutExpired:
            return []
        result_path = overlay_root / "upload" / "upload_wcs_constellations.json"
        if not result_path.is_file():
            return []
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return overlay_from_selected(payload.get("selected") or [], verified=True)


@lru_cache(maxsize=1)
def proper_name_to_hip() -> dict[str, int]:
    """Map DB/HYG proper names to HIP ids used by the browser overlay."""
    if not HYG_CATALOG.is_file():
        return {}
    mapping: dict[str, int] = {}
    with HYG_CATALOG.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            proper = str(row.get("proper") or "").strip().casefold()
            hip = str(row.get("hip") or "").strip()
            if proper and hip:
                try:
                    mapping[proper] = int(float(hip))
                except ValueError:
                    continue
    return mapping


def load_constellation_details(iau_codes: set[str], english_names: set[str]) -> dict[str, dict]:
    """Read localized constellation details and bright named stars from MySQL."""
    if not iau_codes and not english_names:
        return {}

    from database.connection import SessionLocal
    from models.constellation import ConstellationModel
    from models.star import StarModel
    from sqlalchemy import or_

    lookup_codes = set(iau_codes)
    if "Ser" in lookup_codes:
        lookup_codes.update({"SerH", "SerT"})
    db = SessionLocal()
    try:
        constellations = (
            db.query(ConstellationModel)
            .filter(or_(
                ConstellationModel.abbreviation.in_(lookup_codes),
                ConstellationModel.name_en.in_(english_names),
            ))
            .all()
        )
        star_codes = {
            "Ser" if row.abbreviation in {"SerH", "SerT"} else row.abbreviation
            for row in constellations
        }
        stars = (
            db.query(StarModel)
            .filter(StarModel.con.in_(star_codes))
            .filter(StarModel.proper.isnot(None), StarModel.proper != "")
            .filter(StarModel.mag.isnot(None))
            .order_by(StarModel.con.asc(), StarModel.mag.asc())
            .all()
        )
    finally:
        db.close()

    hip_by_name = proper_name_to_hip()
    stars_by_code: dict[str, list[dict]] = {}
    for star in stars:
        bucket = stars_by_code.setdefault(str(star.con), [])
        if len(bucket) >= 3:
            continue
        english = str(star.proper or "").strip()
        bucket.append({
            "ko": str(star.proper_ko or english),
            "en": english,
            "hip": hip_by_name.get(english.casefold()),
            "magnitude": round(float(star.mag), 2),
        })

    details: dict[str, dict] = {}
    for row in sorted(constellations, key=lambda item: item.abbreviation):
        is_serpens = row.abbreviation in {"SerH", "SerT"}
        iau = "Ser" if is_serpens else row.abbreviation
        star_code = "Ser" if is_serpens else row.abbreviation
        payload = {
            "constellationId": row.constellation_id,
            "name": "뱀자리" if is_serpens else row.name_ko,
            "englishName": "Serpens" if is_serpens else row.name_en,
            "abbreviation": iau,
            "description": row.description,
            "story": row.mythology or "등록된 별자리 이야기가 없습니다.",
            "difficulty": row.difficulty,
            "imageUrl": row.image_url,
            "mainStars": stars_by_code.get(star_code, []),
            "detailsSource": "database",
        }
        details.setdefault(iau, payload)
        details.setdefault(str(row.name_en).casefold(), payload)
        if is_serpens:
            details.setdefault("serpens", payload)
    return details


def enrich_recognition_results(rankings: list[dict], overlays: list[dict]) -> None:
    iau_codes = {str(item.get("iau") or "") for item in overlays} - {""}
    english_names = {
        str(item.get("englishName") or item.get("candidate") or "")
        for item in [*rankings, *overlays]
    } - {""}
    try:
        details = load_constellation_details(iau_codes, english_names)
    except Exception:
        # Recognition remains usable while the DB is temporarily unavailable.
        return
    for item in [*rankings, *overlays]:
        key = str(item.get("iau") or "")
        detail = details.get(key) or details.get(
            str(item.get("englishName") or item.get("candidate") or "").casefold()
        )
        if detail:
            item.update(detail)
            if "candidate" in item:
                item["candidate"] = detail["englishName"]


def mark_registration_eligibility(results: list[dict]) -> None:
    """Apply the catalog-registration rule to one recognition result set."""
    if not results:
        return
    if len(results) == 1:
        results[0]["registrationEligible"] = bool(results[0].get("constellationId"))
        return
    has_eighty_or_more = any(float(item.get("score", item.get("percentage", 0))) >= 80 for item in results)
    highest_index = max(
        range(len(results)),
        key=lambda index: float(results[index].get("score", results[index].get("percentage", 0))),
    )
    for index, item in enumerate(results):
        percentage = float(item.get("score", item.get("percentage", 0)))
        meets_score_rule = percentage >= 80 if has_eighty_or_more else index == highest_index
        item["registrationEligible"] = meets_score_rule and bool(item.get("constellationId"))


def model_path() -> Path:
    configured = os.getenv("YOLO_MODEL_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_MODEL.resolve()


@lru_cache(maxsize=1)
def load_model():
    path = model_path()
    if not path.is_file():
        raise FileNotFoundError(f"YOLO 모델 파일이 없습니다: {path}")
    from ultralytics import YOLO

    return YOLO(str(path))


def decode_image(content: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("JPG 또는 PNG 이미지가 아닙니다.") from exc
    return image


def run_graph_matching(content: bytes, suffix: str, yolo_results: list[dict]) -> dict:
    """Run stages 03-05 and return browser-drawable matched points and edges."""
    scripts = PROJECT_ROOT / "Constellation" / "scripts"
    reference_path = (
        PROJECT_ROOT / "Constellation" / "data" / "reference" / "stellarium" / "western" / "index.json"
    )
    with tempfile.TemporaryDirectory(prefix="astra_graph_") as temporary:
        root = Path(temporary)
        image_path = root / f"upload{suffix}"
        image_path.write_bytes(content)
        detection_root, graph_root, matching_root = root / "detection", root / "graph", root / "matching"
        commands = [
            [
                sys.executable, str(scripts / "03_star_detection.py"), str(image_path),
                "--output-dir", str(detection_root), "--sky-fraction", "1.0",
                "--max-stars", "250", "--minimum-usable-stars", "7",
            ],
            [
                sys.executable, str(scripts / "04_star_graph.py"),
                str(detection_root / "upload" / "upload_stars.json"),
                "--output-dir", str(graph_root), "--top-stars", "100",
            ],
            [
                sys.executable, str(scripts / "05_graph_matching.py"),
                str(graph_root / "upload" / "upload_graph.json"),
                "--output-dir", str(matching_root), "--top-results", "10",
            ],
        ]
        try:
            for command in commands:
                completed = subprocess.run(
                    command, cwd=PROJECT_ROOT / "Constellation", capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=30, check=False,
                )
                if completed.returncode != 0:
                    return {"status": "unavailable", "reason": "별 구조 분석을 완료하지 못했습니다."}
        except subprocess.TimeoutExpired:
            return {"status": "unavailable", "reason": "별 구조 분석 제한시간을 초과했습니다."}

        matching_path = matching_root / "upload" / "upload_matching.json"
        if not matching_path.is_file():
            return {"status": "unavailable", "reason": "별 구조 후보를 찾지 못했습니다."}
        matching = json.loads(matching_path.read_text(encoding="utf-8"))
        candidates = matching.get("results") or []
        if not candidates:
            return {"status": "unavailable", "reason": "별 구조 후보를 찾지 못했습니다."}
        best = candidates[0]
        mappings = {int(row["hip"]): row for row in best.get("mappings", [])}
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        template = next(
            (entry for entry in reference.get("constellations", []) if entry.get("iau") == best.get("iau")),
            None,
        )
        edges = []
        if template:
            for line in template.get("lines", []):
                numeric = [int(value) for value in line if isinstance(value, (int, float))]
                for first, second in zip(numeric, numeric[1:]):
                    if first in mappings and second in mappings:
                        edges.append({"from": first, "to": second})
        points = [
            {
                "id": hip,
                "x": round(float(row["observed_x"]), 2),
                "y": round(float(row["observed_y"]), 2),
                "error": round(float(row["error_px"]), 2),
            }
            for hip, row in mappings.items()
        ]
        candidate_english = str(best.get("native_name") or best.get("iau") or "")
        yolo_names = {str(row.get("englishName")) for row in yolo_results}
        confidence = str(matching.get("decision", {}).get("confidence") or "low")
        agrees = candidate_english in yolo_names
        verified = agrees and confidence == "high" and not matching.get("decision", {}).get(
            "requires_plate_solve_verification", True
        )
        return {
            "status": "verified" if verified else "candidate",
            "candidate": candidate_english,
            "iau": best.get("iau"),
            "score": round(float(best.get("score") or 0), 1),
            "confidence": confidence,
            "agreesWithYolo": agrees,
            "verified": verified,
            "points": points,
            "edges": edges,
            "message": "검증된 별자리 연결선입니다." if verified else "구조 분석 후보이며 Plate Solving으로 확정되지 않았습니다.",
        }


def recognize(
    content: bytes, confidence: float = 0.25, suffix: str = ".jpg", filename: str = ""
) -> dict:
    image = decode_image(content)
    portable_result = find_portable_result(content)
    if portable_result is not None:
        enrich_recognition_results(
            portable_result.get("results") or [],
            portable_result.get("graphOverlays") or [],
        )
        registration_results = (
            [item for item in (portable_result.get("graphOverlays") or []) if item.get("verified")]
            or (portable_result.get("results") or [])
        )
        mark_registration_eligibility(registration_results)
        return portable_result
    model = load_model()
    prediction = model.predict(source=image, imgsz=640, conf=confidence, verbose=False)[0]
    names = prediction.names
    width, height = image.size
    detections = []
    grouped: dict[str, dict] = {}

    if prediction.boxes is not None:
        for box in prediction.boxes:
            class_id = int(box.cls.item())
            object_name = str(names[class_id])
            score = float(box.conf.item())
            x1, y1, x2, y2 = [round(float(value), 2) for value in box.xyxy[0].tolist()]
            detection = {
                "classId": class_id,
                "objectName": object_name,
                "confidence": round(score, 4),
                "percentage": round(score * 100, 1),
                "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            }
            detections.append(detection)

            group = OBJECT_TO_GROUP.get(object_name, (object_name, object_name, "object"))
            english_name, korean_name, result_type = group
            current = grouped.setdefault(
                english_name,
                {
                    "name": korean_name,
                    "englishName": english_name,
                    "type": result_type,
                    "confidence": 0.0,
                    "detectedObjects": [],
                },
            )
            current["confidence"] = max(current["confidence"], score)
            if object_name not in current["detectedObjects"]:
                current["detectedObjects"].append(object_name)

    rankings = sorted(grouped.values(), key=lambda item: item["confidence"], reverse=True)
    for rank, item in enumerate(rankings, 1):
        item["rank"] = rank
        item["percentage"] = round(item.pop("confidence") * 100, 1)

    cached_wcs = find_known_wcs(content, filename)
    if cached_wcs:
        plate_solving = {
            "status": "success", "cached": True, "aiUsed": False,
            "source": "legacy-wcs-cache", "message": "기존 WCS 천구 좌표를 확인했습니다.",
        }
        resolved_wcs = cached_wcs
    else:
        plate_solving, resolved_wcs = run_realtime_plate_solving(content, suffix)
    verified_overlays = run_wcs_overlay(content, suffix, resolved_wcs) if resolved_wcs else []
    graph_overlay = run_graph_matching(content, suffix, rankings) if not verified_overlays else {}
    graph_overlays = verified_overlays or ([graph_overlay] if graph_overlay.get("points") else [])
    enrich_recognition_results(rankings, graph_overlays)
    registration_results = [item for item in graph_overlays if item.get("verified")] or rankings
    mark_registration_eligibility(registration_results)
    return {
        "model": str(model_path()),
        "image": {"width": width, "height": height},
        "detectionCount": len(detections),
        "detections": detections,
        "results": rankings,
        "graphOverlay": graph_overlays[0] if graph_overlays else graph_overlay,
        "graphOverlays": graph_overlays,
        "wcsVerified": bool(verified_overlays),
        "plateSolving": plate_solving,
        "message": (
            "WCS 좌표로 별자리 구조를 확인했습니다."
            if verified_overlays else
            "천체 후보를 찾았습니다."
            if rankings else
            "학습된 8개 천체 후보를 찾지 못했습니다."
        ),
    }
