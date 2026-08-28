"""Match an observed star graph against Stellarium Western constellation patterns."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYG = PROJECT_ROOT / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv"
DEFAULT_STELLARIUM = PROJECT_ROOT / "data" / "reference" / "stellarium" / "western" / "index.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "graph_matching"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path, help="04단계에서 생성한 *_graph.json")
    parser.add_argument("--hyg", type=Path, default=DEFAULT_HYG)
    parser.add_argument("--stellarium", type=Path, default=DEFAULT_STELLARIUM)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="사진 이름별 하위 폴더를 생성할 결과 상위 폴더",
    )
    parser.add_argument("--top-results", type=int, default=10)
    parser.add_argument(
        "--ratio-tolerance",
        type=float,
        default=0.035,
        help="삼각형 변 길이 비율 허용 오차 (기본값: 0.035)",
    )
    parser.add_argument("--max-observed-triangles", type=int, default=200)
    parser.add_argument("--max-hypotheses", type=int, default=120)
    parser.add_argument(
        "--match-radius-factor",
        type=float,
        default=0.12,
        help="기준 별 간격 대비 일치 반경 (기본값: 0.12)",
    )
    parser.add_argument("--minimum-template-stars", type=int, default=3)
    return parser.parse_args()


def read_image(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"원본 이미지 파일을 찾을 수 없습니다: {path}")
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"이미지를 읽을 수 없습니다: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    success, encoded = cv2.imencode(path.suffix or ".jpg", image)
    if not success:
        raise RuntimeError(f"이미지 인코딩에 실패했습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(path)


def load_observed_graph(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"그래프 JSON을 찾을 수 없습니다: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = ("nodes", "triangles", "image", "width", "height")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"그래프 JSON 필수 항목이 없습니다: {', '.join(missing)}")
    if len(payload["nodes"]) < 3 or not payload["triangles"]:
        raise ValueError("그래프에 매칭 가능한 노드 또는 삼각형이 없습니다.")
    return payload


def line_hips(line: list[Any]) -> list[int]:
    """Return numeric HIP identifiers, ignoring optional Stellarium style tokens."""
    return [int(value) for value in line if isinstance(value, (int, float))]


def stellarium_entries(path: Path) -> tuple[list[dict[str, Any]], set[int]]:
    if not path.is_file():
        raise FileNotFoundError(f"Stellarium index.json을 찾을 수 없습니다: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("constellations")
    if not isinstance(entries, list):
        raise ValueError("Stellarium JSON에 constellations 배열이 없습니다.")
    required_hips = {
        hip
        for entry in entries
        for line in entry.get("lines", [])
        for hip in line_hips(line)
    }
    return entries, required_hips


def load_hyg_stars(path: Path, required_hips: set[int]) -> dict[int, dict[str, float]]:
    if not path.is_file():
        raise FileNotFoundError(f"HYG CSV를 찾을 수 없습니다: {path}")
    stars: dict[int, dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            raw_hip = row.get("hip", "").strip()
            if not raw_hip:
                continue
            hip = int(raw_hip)
            if hip not in required_hips:
                continue
            try:
                candidate = {
                    "ra_deg": float(row["ra"]) * 15.0,
                    "dec_deg": float(row["dec"]),
                    "mag": float(row["mag"]),
                }
            except (TypeError, ValueError):
                continue
            previous = stars.get(hip)
            if previous is None or candidate["mag"] < previous["mag"]:
                stars[hip] = candidate
    return stars


def project_sky(hips: list[int], hyg: dict[int, dict[str, float]]) -> np.ndarray:
    ra = np.radians([hyg[hip]["ra_deg"] for hip in hips])
    dec = np.radians([hyg[hip]["dec_deg"] for hip in hips])
    vectors = np.column_stack((np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)))
    center = vectors.mean(axis=0)
    center /= np.linalg.norm(center)
    ra0 = math.atan2(center[1], center[0])
    dec0 = math.asin(float(center[2]))
    delta_ra = (ra - ra0 + math.pi) % (2 * math.pi) - math.pi
    denominator = (
        math.sin(dec0) * np.sin(dec)
        + math.cos(dec0) * np.cos(dec) * np.cos(delta_ra)
    )
    if np.any(denominator <= 1e-6):
        raise ValueError("접평면에 투영할 수 없는 별 좌표가 포함되어 있습니다.")
    x = np.cos(dec) * np.sin(delta_ra) / denominator
    y = (
        math.cos(dec0) * np.sin(dec)
        - math.sin(dec0) * np.cos(dec) * np.cos(delta_ra)
    ) / denominator
    points = np.column_stack((x, y))
    points -= points.mean(axis=0)
    rms = math.sqrt(float(np.mean(np.sum(points * points, axis=1))))
    if rms <= 1e-10:
        raise ValueError("기준 별자리 좌표가 한 점에 모여 있습니다.")
    return points / rms


def build_templates(
    entries: list[dict[str, Any]],
    hyg: dict[int, dict[str, float]],
    minimum_stars: int,
) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for entry in entries:
        lines = entry.get("lines", [])
        numeric_lines = [line_hips(line) for line in lines]
        hips = sorted({hip for line in numeric_lines for hip in line if hip in hyg})
        if len(hips) < minimum_stars:
            continue
        hip_to_index = {hip: index for index, hip in enumerate(hips)}
        edges = {
            tuple(sorted((hip_to_index[int(first)], hip_to_index[int(second)])))
            for line in numeric_lines
            for first, second in zip(line, line[1:])
            if first in hip_to_index and second in hip_to_index and first != second
        }
        if not edges:
            continue
        try:
            points = project_sky(hips, hyg)
        except ValueError:
            continue
        common_name = entry.get("common_name") or {}
        templates.append(
            {
                "iau": entry.get("iau", ""),
                "english_name": common_name.get("english", ""),
                "native_name": common_name.get("native", ""),
                "hips": hips,
                "points": points,
                "magnitudes": [hyg[hip]["mag"] for hip in hips],
                "edges": sorted(edges),
            }
        )
    if not templates:
        raise ValueError("사용 가능한 기준 별자리 템플릿이 없습니다.")
    return templates


def triangle_signature(points: np.ndarray, indices: tuple[int, int, int]) -> dict[str, Any] | None:
    triangle = points[list(indices)]
    opposite_lengths = np.array(
        [
            np.linalg.norm(triangle[1] - triangle[2]),
            np.linalg.norm(triangle[0] - triangle[2]),
            np.linalg.norm(triangle[0] - triangle[1]),
        ],
        dtype=np.float64,
    )
    order = np.argsort(opposite_lengths)
    sorted_lengths = opposite_lengths[order]
    longest = float(sorted_lengths[2])
    if longest <= 1e-10 or float(sorted_lengths[0] / longest) < 0.18:
        return None
    first_vector = triangle[1] - triangle[0]
    second_vector = triangle[2] - triangle[0]
    cross = abs(float(first_vector[0] * second_vector[1] - first_vector[1] * second_vector[0]))
    if cross / (longest * longest) < 0.035:
        return None
    canonical_indices = tuple(indices[int(index)] for index in order)
    return {
        "indices": canonical_indices,
        "ratio_short": float(sorted_lengths[0] / longest),
        "ratio_middle": float(sorted_lengths[1] / longest),
        "area_strength": cross / (longest * longest),
    }


def observed_triangles(graph: dict[str, Any], maximum: int) -> tuple[np.ndarray, list[dict[str, Any]]]:
    nodes = graph["nodes"]
    points = np.array([[float(node["x"]), float(node["y"])] for node in nodes], dtype=np.float64)
    id_to_index = {int(node["star_id"]): index for index, node in enumerate(nodes)}
    signatures: list[dict[str, Any]] = []
    for row in graph["triangles"]:
        try:
            indices = tuple(
                id_to_index[int(row[key])]
                for key in ("star_a_id", "star_b_id", "star_c_id")
            )
        except (KeyError, ValueError):
            continue
        signature = triangle_signature(points, indices)
        if signature is not None:
            signatures.append(signature)
    signatures.sort(key=lambda item: item["area_strength"], reverse=True)
    return points, signatures[:maximum]


def reference_triangles(points: np.ndarray) -> list[dict[str, Any]]:
    signatures: list[dict[str, Any]] = []
    for indices in itertools.combinations(range(len(points)), 3):
        signature = triangle_signature(points, indices)
        if signature is not None:
            signatures.append(signature)
    return signatures


def fit_similarity(source: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, bool]:
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    source_centered = source - source_center
    target_centered = target - target_center
    covariance = source_centered.T @ target_centered
    left, singular, right_transposed = np.linalg.svd(covariance)
    rotation = left @ right_transposed
    denominator = float(np.sum(source_centered * source_centered))
    if denominator <= 1e-12:
        raise ValueError("유사변환을 계산할 수 없는 기준 삼각형입니다.")
    scale = float(np.sum(singular) / denominator)
    translation = target_center - scale * (source_center @ rotation)
    reflected = bool(np.linalg.det(rotation) < 0)
    return scale, rotation, translation, reflected


def transform_points(
    points: np.ndarray, scale: float, rotation: np.ndarray, translation: np.ndarray
) -> np.ndarray:
    return scale * (points @ rotation) + translation


def greedy_matches(
    predicted: np.ndarray,
    observed: np.ndarray,
    visible_indices: list[int],
    threshold: float,
) -> list[tuple[int, int, float]]:
    candidates: list[tuple[float, int, int]] = []
    for reference_index in visible_indices:
        distances = np.linalg.norm(observed - predicted[reference_index], axis=1)
        for observed_index in np.flatnonzero(distances <= threshold):
            candidates.append((float(distances[observed_index]), reference_index, int(observed_index)))
    matches: list[tuple[int, int, float]] = []
    used_reference: set[int] = set()
    used_observed: set[int] = set()
    for error, reference_index, observed_index in sorted(candidates):
        if reference_index in used_reference or observed_index in used_observed:
            continue
        used_reference.add(reference_index)
        used_observed.add(observed_index)
        matches.append((reference_index, observed_index, error))
    return matches


def evaluate_hypothesis(
    template: dict[str, Any],
    observed_points: np.ndarray,
    reference_triangle: dict[str, Any],
    observed_triangle: dict[str, Any],
    width: int,
    height: int,
    match_radius_factor: float,
) -> dict[str, Any] | None:
    source = template["points"][list(reference_triangle["indices"])]
    target = observed_points[list(observed_triangle["indices"])]
    try:
        scale, rotation, translation, reflected = fit_similarity(source, target)
    except ValueError:
        return None
    if not math.isfinite(scale) or scale <= 0:
        return None
    predicted = transform_points(template["points"], scale, rotation, translation)
    visible = [
        index
        for index, (x, y) in enumerate(predicted)
        if -0.02 * width <= x <= 1.02 * width and -0.02 * height <= y <= 1.02 * height
    ]
    if len(visible) < 3:
        return None

    transformed_edge_lengths = [
        float(np.linalg.norm(predicted[first] - predicted[second]))
        for first, second in template["edges"]
        if first in visible and second in visible
    ]
    if transformed_edge_lengths:
        reference_spacing = float(np.median(transformed_edge_lengths))
    else:
        visible_points = predicted[visible]
        pairwise = [
            float(np.linalg.norm(visible_points[a] - visible_points[b]))
            for a, b in itertools.combinations(range(len(visible_points)), 2)
        ]
        reference_spacing = float(np.median(pairwise))
    threshold = max(8.0, reference_spacing * match_radius_factor)
    matches = greedy_matches(predicted, observed_points, visible, threshold)
    if len(matches) < 3:
        return None

    matched_reference = {item[0] for item in matches}
    visible_edges = [
        edge for edge in template["edges"] if edge[0] in visible and edge[1] in visible
    ]
    matched_edges = sum(
        first in matched_reference and second in matched_reference
        for first, second in visible_edges
    )
    coverage = len(matches) / len(visible)
    verified_matches = max(0, len(matches) - 3)
    verification = verified_matches / max(1, len(visible) - 3)
    edge_coverage = matched_edges / max(1, len(visible_edges))
    rms = math.sqrt(sum(error * error for _, _, error in matches) / len(matches))
    closeness = math.exp(-rms / threshold)
    support = min(1.0, verified_matches / 4.0)
    raw_score = 100.0 * (
        0.50 * verification + 0.25 * coverage + 0.15 * edge_coverage + 0.10 * closeness
    )
    score = raw_score * (0.50 + 0.50 * support)
    angle = math.degrees(math.atan2(float(rotation[0, 1]), float(rotation[0, 0])))
    return {
        "score": score,
        "matched_stars": len(matches),
        "verified_matches_beyond_seed": verified_matches,
        "visible_reference_stars": len(visible),
        "total_reference_stars": len(template["hips"]),
        "coverage": coverage,
        "matched_edges": matched_edges,
        "visible_reference_edges": len(visible_edges),
        "rms_error_px": rms,
        "match_radius_px": threshold,
        "scale": scale,
        "rotation_degrees": angle,
        "reflected": reflected,
        "rotation_matrix": rotation.tolist(),
        "translation": translation.tolist(),
        "predicted": predicted.tolist(),
        "matches": matches,
        "seed_reference_indices": list(reference_triangle["indices"]),
        "seed_observed_indices": list(observed_triangle["indices"]),
        "ratio_error": abs(reference_triangle["ratio_short"] - observed_triangle["ratio_short"])
        + abs(reference_triangle["ratio_middle"] - observed_triangle["ratio_middle"]),
    }


def match_template(
    template: dict[str, Any],
    observed_points: np.ndarray,
    observed_signatures: list[dict[str, Any]],
    width: int,
    height: int,
    ratio_tolerance: float,
    max_hypotheses: int,
    match_radius_factor: float,
) -> dict[str, Any] | None:
    candidates: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for reference in reference_triangles(template["points"]):
        for observed in observed_signatures:
            short_error = abs(reference["ratio_short"] - observed["ratio_short"])
            middle_error = abs(reference["ratio_middle"] - observed["ratio_middle"])
            if short_error <= ratio_tolerance and middle_error <= ratio_tolerance:
                candidates.append((short_error + middle_error, reference, observed))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    best: dict[str, Any] | None = None
    for _, reference, observed in candidates[:max_hypotheses]:
        result = evaluate_hypothesis(
            template,
            observed_points,
            reference,
            observed,
            width,
            height,
            match_radius_factor,
        )
        if result is None:
            continue
        if best is None or (
            result["score"], result["matched_stars"], -result["rms_error_px"]
        ) > (best["score"], best["matched_stars"], -best["rms_error_px"]):
            best = result
    if best is None:
        return None
    return {
        "iau": template["iau"],
        "english_name": template["english_name"],
        "native_name": template["native_name"],
        **best,
    }


def confidence_decision(results: list[dict[str, Any]]) -> tuple[str, str, float]:
    if not results:
        return "none", "판정 가능한 후보가 없습니다.", 0.0
    best = results[0]
    margin = best["score"] - results[1]["score"] if len(results) > 1 else best["score"]
    verified = best["verified_matches_beyond_seed"]
    verification_fraction = verified / max(1, best["visible_reference_stars"] - 3)
    if best["matched_stars"] >= 7 and verified >= 4 and verification_fraction >= 0.60 and best["score"] >= 70 and margin >= 5:
        return "high", "상위 후보가 충분한 추가 별과 간선으로 검증되었습니다.", margin
    if best["matched_stars"] >= 6 and verified >= 3 and verification_fraction >= 0.40 and best["score"] >= 55:
        return "medium", "유력 후보이지만 촬영 정보 또는 Plate Solving 검증이 필요합니다.", margin
    return "low", "그래프만으로 확정하기 어려워 후보로만 사용해야 합니다.", margin


def serializable_result(
    result: dict[str, Any],
    template: dict[str, Any],
    observed_nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    mappings = []
    for reference_index, observed_index, error in result["matches"]:
        predicted_x, predicted_y = result["predicted"][reference_index]
        node = observed_nodes[observed_index]
        mappings.append(
            {
                "hip": template["hips"][reference_index],
                "magnitude": round(template["magnitudes"][reference_index], 4),
                "observed_star_id": int(node["star_id"]),
                "predicted_x": round(predicted_x, 3),
                "predicted_y": round(predicted_y, 3),
                "observed_x": round(float(node["x"]), 3),
                "observed_y": round(float(node["y"]), 3),
                "error_px": round(error, 3),
            }
        )
    excluded = {
        "predicted",
        "matches",
        "rotation_matrix",
        "translation",
        "seed_reference_indices",
        "seed_observed_indices",
    }
    payload = {key: value for key, value in result.items() if key not in excluded}
    payload.update(
        {
            "score": round(result["score"], 4),
            "coverage": round(result["coverage"], 6),
            "rms_error_px": round(result["rms_error_px"], 4),
            "match_radius_px": round(result["match_radius_px"], 4),
            "scale": round(result["scale"], 8),
            "rotation_degrees": round(result["rotation_degrees"], 4),
            "ratio_error": round(result["ratio_error"], 8),
            "transform": {
                "rotation_matrix": result["rotation_matrix"],
                "translation": result["translation"],
            },
            "seed_triangle": {
                "hips": [template["hips"][index] for index in result["seed_reference_indices"]],
                "observed_star_ids": [
                    int(observed_nodes[index]["star_id"])
                    for index in result["seed_observed_indices"]
                ],
            },
            "mappings": mappings,
        }
    )
    return payload


def annotate_best(
    image: np.ndarray,
    result: dict[str, Any] | None,
    template: dict[str, Any] | None,
    confidence: str,
) -> np.ndarray:
    annotated = image.copy()
    if result is not None and template is not None:
        predicted = np.asarray(result["predicted"], dtype=np.float64)
        matched_indices = {item[0] for item in result["matches"]}
        overlay = annotated.copy()
        for first, second in template["edges"]:
            first_point = predicted[first]
            second_point = predicted[second]
            if (
                -100 <= first_point[0] <= image.shape[1] + 100
                and -100 <= first_point[1] <= image.shape[0] + 100
                and -100 <= second_point[0] <= image.shape[1] + 100
                and -100 <= second_point[1] <= image.shape[0] + 100
            ):
                cv2.line(
                    overlay,
                    tuple(np.round(first_point).astype(int)),
                    tuple(np.round(second_point).astype(int)),
                    (40, 210, 255),
                    5,
                    cv2.LINE_AA,
                )
        annotated = cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0)
        for index, point in enumerate(predicted):
            if not (0 <= point[0] < image.shape[1] and 0 <= point[1] < image.shape[0]):
                continue
            center = tuple(np.round(point).astype(int))
            color = (40, 255, 40) if index in matched_indices else (40, 40, 255)
            cv2.circle(annotated, center, 11, color, 3, cv2.LINE_AA)
            cv2.putText(
                annotated,
                str(template["hips"][index]),
                (center[0] + 12, center[1] - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

    panel_height = max(85, round(image.shape[0] * 0.075))
    cv2.rectangle(annotated, (0, 0), (image.shape[1], panel_height), (0, 0, 0), -1)
    if result is None:
        title = "No constellation candidate"
        detail = "confidence=none"
    else:
        title = f"Candidate: {result['iau']} / {result['english_name']}"
        detail = (
            f"score={result['score']:.1f}  matched={result['matched_stars']}/"
            f"{result['visible_reference_stars']}  confidence={confidence}"
        )
    font_scale = max(0.65, image.shape[1] / 5000)
    cv2.putText(annotated, title, (24, round(panel_height * 0.43)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated, detail, (24, round(panel_height * 0.80)), cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (180, 230, 255), 2, cv2.LINE_AA)
    return annotated


def draw_dashed_line(
    image: np.ndarray,
    first: tuple[int, int],
    second: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int,
    dash_length: float = 18.0,
) -> None:
    delta_x = second[0] - first[0]
    delta_y = second[1] - first[1]
    length = math.hypot(delta_x, delta_y)
    if length <= 1e-6:
        return
    unit_x, unit_y = delta_x / length, delta_y / length
    position = 0.0
    while position < length:
        end_position = min(position + dash_length, length)
        start_point = (
            round(first[0] + unit_x * position),
            round(first[1] + unit_y * position),
        )
        end_point = (
            round(first[0] + unit_x * end_position),
            round(first[1] + unit_y * end_position),
        )
        cv2.line(image, start_point, end_point, color, thickness, cv2.LINE_AA)
        position += dash_length * 1.8


def selection_explanation(
    result: dict[str, Any] | None,
    confidence: str,
    reason: str,
    score_margin: float,
    used_observed_triangles: int,
) -> list[str]:
    if result is None:
        return [
            f"안정적인 관측 삼각형 {used_observed_triangles:,}개를 비교했습니다.",
            "기준을 만족한 별자리 후보가 없습니다.",
        ]
    return [
        f"안정적인 관측 삼각형 {used_observed_triangles:,}개에서 모양 후보를 탐색했습니다.",
        (
            f"초기 삼각형 3개 별 외에 {result['verified_matches_beyond_seed']}개 별이 "
            "추가로 일치했습니다."
        ),
        (
            f"화면 안 기준 별 {result['visible_reference_stars']}개 중 "
            f"{result['matched_stars']}개, 기준 연결선 {result['visible_reference_edges']}개 중 "
            f"{result['matched_edges']}개가 일치했습니다."
        ),
        (
            f"위치 RMS 오차 {result['rms_error_px']:.2f}px가 허용 반경 "
            f"{result['match_radius_px']:.2f}px 안에 있습니다."
        ),
        (
            f"종합 점수 {result['score']:.2f}, 2위와의 점수 차이 {score_margin:.2f}, "
            f"신뢰도 {confidence}: {reason}"
        ),
    ]


def create_selection_image(
    image: np.ndarray,
    graph: dict[str, Any],
    result: dict[str, Any] | None,
    template: dict[str, Any] | None,
    confidence: str,
    score_margin: float,
    used_observed_triangles: int,
) -> np.ndarray:
    """Show how the Delaunay graph led to the selected reference pattern."""
    canvas = cv2.addWeighted(image, 0.48, np.zeros_like(image), 0.52, 0)
    graph_nodes = {int(node["star_id"]): node for node in graph["nodes"]}

    delaunay_overlay = canvas.copy()
    for edge in graph["edges"]:
        first = graph_nodes[int(edge["source_id"])]
        second = graph_nodes[int(edge["target_id"])]
        cv2.line(
            delaunay_overlay,
            (round(float(first["x"])), round(float(first["y"]))),
            (round(float(second["x"])), round(float(second["y"]))),
            (190, 120, 35),
            2,
            cv2.LINE_AA,
        )
    canvas = cv2.addWeighted(delaunay_overlay, 0.55, canvas, 0.45, 0)

    if result is not None and template is not None:
        predicted = np.asarray(result["predicted"], dtype=np.float64)
        observed_points = np.asarray(
            [[float(node["x"]), float(node["y"])] for node in graph["nodes"]],
            dtype=np.float64,
        )
        mapping = {
            reference_index: (observed_index, error)
            for reference_index, observed_index, error in result["matches"]
        }
        seed_observed = set(result["seed_observed_indices"])

        seed_points = observed_points[result["seed_observed_indices"]]
        for first, second in ((0, 1), (1, 2), (2, 0)):
            cv2.line(
                canvas,
                tuple(np.round(seed_points[first]).astype(int)),
                tuple(np.round(seed_points[second]).astype(int)),
                (220, 40, 220),
                4,
                cv2.LINE_AA,
            )

        for first, second in template["edges"]:
            first_match = mapping.get(first)
            second_match = mapping.get(second)
            if first_match is not None and second_match is not None:
                first_point = observed_points[first_match[0]]
                second_point = observed_points[second_match[0]]
                cv2.line(
                    canvas,
                    tuple(np.round(first_point).astype(int)),
                    tuple(np.round(second_point).astype(int)),
                    (0, 225, 255),
                    9,
                    cv2.LINE_AA,
                )
            else:
                first_point = predicted[first]
                second_point = predicted[second]
                if (
                    -100 <= first_point[0] <= image.shape[1] + 100
                    and -100 <= first_point[1] <= image.shape[0] + 100
                    and -100 <= second_point[0] <= image.shape[1] + 100
                    and -100 <= second_point[1] <= image.shape[0] + 100
                ):
                    draw_dashed_line(
                        canvas,
                        tuple(np.round(first_point).astype(int)),
                        tuple(np.round(second_point).astype(int)),
                        (40, 70, 255),
                        4,
                    )

        for reference_index, (observed_index, error) in mapping.items():
            point = tuple(np.round(observed_points[observed_index]).astype(int))
            is_seed = observed_index in seed_observed
            color = (220, 40, 220) if is_seed else (40, 255, 40)
            label = "SEED" if is_seed else "VERIFY"
            cv2.circle(canvas, point, 16, color, 4, cv2.LINE_AA)
            cv2.putText(
                canvas,
                f"{label} HIP {template['hips'][reference_index]} / S{graph['nodes'][observed_index]['star_id']}",
                (point[0] + 18, point[1] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                max(0.48, image.shape[1] / 6000),
                color,
                2,
                cv2.LINE_AA,
            )

        matched_reference = set(mapping)
        for reference_index, point in enumerate(predicted):
            if reference_index in matched_reference:
                continue
            if not (0 <= point[0] < image.shape[1] and 0 <= point[1] < image.shape[0]):
                continue
            center = tuple(np.round(point).astype(int))
            cv2.circle(canvas, center, 16, (40, 40, 255), 4, cv2.LINE_AA)
            cv2.putText(
                canvas,
                f"MISS HIP {template['hips'][reference_index]}",
                (center[0] + 18, center[1] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                max(0.48, image.shape[1] / 6000),
                (40, 40, 255),
                2,
                cv2.LINE_AA,
            )

    panel_height = max(220, round(image.shape[0] * 0.13))
    cv2.rectangle(canvas, (0, 0), (image.shape[1], panel_height), (0, 0, 0), -1)
    if result is None:
        lines = ["Selection process: no candidate", f"Observed stable triangles: {used_observed_triangles}"]
    else:
        lines = [
            f"Selection: {result['iau']} / {result['native_name']} ({result['english_name']})",
            (
                f"Observed triangles={used_observed_triangles} | seed=3 | "
                f"additional verified={result['verified_matches_beyond_seed']}"
            ),
            (
                f"Matched stars={result['matched_stars']}/{result['visible_reference_stars']} | "
                f"matched reference edges={result['matched_edges']}/{result['visible_reference_edges']} | "
                f"RMS={result['rms_error_px']:.1f}px <= radius={result['match_radius_px']:.1f}px"
            ),
            f"Score={result['score']:.1f} | margin={score_margin:.1f} | confidence={confidence}",
            "CYAN=Delaunay  MAGENTA=seed triangle  GREEN=verified star  YELLOW=matched line  RED=missing",
        ]
    font_scale = max(0.50, image.shape[1] / 4200)
    line_height = panel_height / (len(lines) + 0.5)
    for index, line in enumerate(lines):
        color = (255, 255, 255) if index < len(lines) - 1 else (180, 230, 255)
        cv2.putText(
            canvas,
            line,
            (20, round((index + 1) * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale if index else font_scale * 1.12,
            color,
            2,
            cv2.LINE_AA,
        )
    return canvas


def output_stem(path: Path) -> str:
    stem = path.stem
    return stem[:-6] if stem.endswith("_graph") else stem


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if args.top_results < 1 or args.max_observed_triangles < 1 or args.max_hypotheses < 1:
        raise ValueError("결과 및 후보 개수 제한은 1 이상이어야 합니다.")
    if args.ratio_tolerance <= 0 or args.match_radius_factor <= 0:
        raise ValueError("허용 오차 값은 0보다 커야 합니다.")
    if args.minimum_template_stars < 3:
        raise ValueError("minimum-template-stars는 3 이상이어야 합니다.")

    graph_path = args.graph.resolve()
    graph = load_observed_graph(graph_path)
    image_path = Path(graph["image"]).resolve()
    image = read_image(image_path)
    height, width = image.shape[:2]
    if (width, height) != (int(graph["width"]), int(graph["height"])):
        raise ValueError("그래프 메타데이터와 원본 이미지 크기가 다릅니다.")

    entries, required_hips = stellarium_entries(args.stellarium.resolve())
    hyg = load_hyg_stars(args.hyg.resolve(), required_hips)
    templates = build_templates(entries, hyg, args.minimum_template_stars)
    observed_points, observed_signatures = observed_triangles(graph, args.max_observed_triangles)
    if not observed_signatures:
        raise ValueError("안정적인 관측 삼각형이 없습니다.")

    template_by_iau = {template["iau"]: template for template in templates}
    results: list[dict[str, Any]] = []
    for template in templates:
        result = match_template(
            template,
            observed_points,
            observed_signatures,
            width,
            height,
            args.ratio_tolerance,
            args.max_hypotheses,
            args.match_radius_factor,
        )
        if result is not None:
            results.append(result)
    results.sort(key=lambda item: (-item["score"], -item["matched_stars"], item["rms_error_px"]))
    top_results = results[: args.top_results]
    confidence, reason, score_margin = confidence_decision(top_results)
    serialized = [
        serializable_result(result, template_by_iau[result["iau"]], graph["nodes"])
        for result in top_results
    ]

    stem = output_stem(graph_path)
    output_dir = args.output_dir.resolve() / stem
    output_dir.mkdir(parents=True, exist_ok=True)
    ranking_path = output_dir / f"{stem}_matches.csv"
    mapping_path = output_dir / f"{stem}_best_mapping.csv"
    json_path = output_dir / f"{stem}_matching.json"
    selection_path = output_dir / f"{stem}_selection.jpg"
    image_output_path = output_dir / f"{stem}_matched.jpg"
    ranking_rows = [
        {
            "rank": rank,
            **result,
            "score_margin_from_best": round(serialized[0]["score"] - result["score"], 4) if serialized else 0,
        }
        for rank, result in enumerate(serialized, start=1)
    ]
    ranking_fields = [
        "rank", "iau", "english_name", "native_name", "score", "score_margin_from_best",
        "matched_stars", "verified_matches_beyond_seed", "visible_reference_stars",
        "total_reference_stars", "coverage", "matched_edges", "visible_reference_edges",
        "rms_error_px", "match_radius_px", "rotation_degrees", "reflected", "ratio_error",
    ]
    write_csv(ranking_path, ranking_rows, ranking_fields)
    mapping_rows = serialized[0]["mappings"] if serialized else []
    mapping_fields = [
        "hip", "magnitude", "observed_star_id", "predicted_x", "predicted_y",
        "observed_x", "observed_y", "error_px",
    ]
    write_csv(mapping_path, mapping_rows, mapping_fields)
    best = top_results[0] if top_results else None
    best_template = template_by_iau[best["iau"]] if best else None
    explanation = selection_explanation(
        best,
        confidence,
        reason,
        score_margin,
        len(observed_signatures),
    )
    payload = {
        "source_graph": str(graph_path),
        "image": str(image_path),
        "reference": {
            "stellarium": str(args.stellarium.resolve()),
            "hyg": str(args.hyg.resolve()),
            "templates_tested": len(templates),
        },
        "parameters": {
            "ratio_tolerance": args.ratio_tolerance,
            "max_observed_triangles": args.max_observed_triangles,
            "used_observed_triangles": len(observed_signatures),
            "max_hypotheses_per_constellation": args.max_hypotheses,
            "match_radius_factor": args.match_radius_factor,
            "minimum_template_stars": args.minimum_template_stars,
        },
        "decision": {
            "confidence": confidence,
            "reason": reason,
            "best_second_score_margin": round(score_margin, 4),
            "requires_plate_solve_verification": confidence != "high",
            "selection_explanation": explanation,
        },
        "results": serialized,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    selection_image = create_selection_image(
        image,
        graph,
        best,
        best_template,
        confidence,
        score_margin,
        len(observed_signatures),
    )
    write_image(selection_path, selection_image)
    annotated = annotate_best(image, best, best_template, confidence)
    write_image(image_output_path, annotated)

    print(f"기준 별자리 템플릿: {len(templates):,}개")
    print(f"사용한 관측 삼각형: {len(observed_signatures):,}개")
    if best:
        print(f"최상위 후보: {best['iau']} / {best['english_name']}")
        print(f"점수: {best['score']:.2f}")
        print(f"일치 별: {best['matched_stars']}/{best['visible_reference_stars']}개")
        print(f"신뢰도: {confidence}")
        print(f"주의: {reason}")
        print("선택 근거:")
        for line in explanation:
            print(f"  - {line}")
    else:
        print("최상위 후보: 없음")
    print(f"matches_csv: {ranking_path}")
    print(f"mapping_csv: {mapping_path}")
    print(f"matching_json: {json_path}")
    print(f"selection_image: {selection_path}")
    print(f"matched_image: {image_output_path}")


if __name__ == "__main__":
    main()
