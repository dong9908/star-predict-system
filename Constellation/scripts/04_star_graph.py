"""Build a local geometric graph from detected star candidates."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "star_graph"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stars", type=Path, help="03단계에서 생성한 *_stars.json 또는 CSV")
    parser.add_argument("--image", type=Path, help="CSV 입력 시 사용할 원본 이미지")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="사진 이름별 하위 폴더를 생성할 결과 상위 폴더",
    )
    parser.add_argument(
        "--top-stars",
        type=int,
        default=100,
        help="검출 점수순으로 그래프에 사용할 최대 별 개수 (기본값: 100)",
    )
    parser.add_argument(
        "--max-edge-factor",
        type=float,
        default=2.5,
        help="Delaunay 간선 중앙값의 몇 배까지 유지할지 지정 (기본값: 2.5)",
    )
    parser.add_argument("--label-top", type=int, default=30)
    parser.add_argument(
        "--keep-all-edges",
        action="store_true",
        help="길이가 긴 Delaunay 간선도 제거하지 않음",
    )
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


def number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} 값이 숫자가 아닙니다: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} 값이 유한한 숫자가 아닙니다: {value!r}")
    return result


def normalize_star(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "star_id": int(number(row.get("star_id"), "star_id")),
        "x": number(row.get("x"), "x"),
        "y": number(row.get("y"), "y"),
        "x_normalized": number(row.get("x_normalized", 0), "x_normalized"),
        "y_normalized": number(row.get("y_normalized", 0), "y_normalized"),
        "score": number(row.get("score", 0), "score"),
        "peak_gray": int(number(row.get("peak_gray", 0), "peak_gray")),
    }


def load_stars(path: Path, image_override: Path | None) -> tuple[list[dict[str, Any]], Path, int, int]:
    if not path.is_file():
        raise FileNotFoundError(f"별 검출 결과를 찾을 수 없습니다: {path}")

    image_path: Path | None = image_override
    width = height = 0
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("stars")
        if not isinstance(rows, list):
            raise ValueError("JSON에 stars 배열이 없습니다.")
        if image_path is None and payload.get("image"):
            image_path = Path(payload["image"])
        width = int(payload.get("width", 0))
        height = int(payload.get("height", 0))
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        sibling_json = path.with_suffix(".json")
        if sibling_json.is_file():
            metadata = json.loads(sibling_json.read_text(encoding="utf-8"))
            if image_path is None and metadata.get("image"):
                image_path = Path(metadata["image"])
            width = int(metadata.get("width", 0))
            height = int(metadata.get("height", 0))
    else:
        raise ValueError("입력 형식은 *_stars.json 또는 CSV여야 합니다.")

    if image_path is None:
        raise ValueError("원본 이미지 경로를 확인할 수 없습니다. --image를 지정해주세요.")
    image_path = image_path.resolve()
    stars = [normalize_star(row) for row in rows]
    if len(stars) < 3:
        raise ValueError("Delaunay 그래프에는 서로 다른 별 후보가 최소 3개 필요합니다.")

    if width <= 0 or height <= 0:
        image = read_image(image_path)
        height, width = image.shape[:2]
    for star in stars:
        if star["x_normalized"] == 0 and star["x"] != 0:
            star["x_normalized"] = star["x"] / width
        if star["y_normalized"] == 0 and star["y"] != 0:
            star["y_normalized"] = star["y"] / height
    return stars, image_path, width, height


def choose_nodes(stars: list[dict[str, Any]], top_stars: int) -> list[dict[str, Any]]:
    if top_stars < 3:
        raise ValueError("top-stars는 3 이상이어야 합니다.")
    ranked = sorted(stars, key=lambda item: (-item["score"], item["star_id"]))[:top_stars]
    unique: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for star in ranked:
        coordinate = (round(star["x"], 5), round(star["y"], 5))
        if coordinate not in seen:
            seen.add(coordinate)
            unique.append(star)
    if len(unique) < 3:
        raise ValueError("중복 좌표를 제거한 뒤 별 후보가 3개 미만입니다.")
    return unique


def delaunay_triangles(
    nodes: list[dict[str, Any]], width: int, height: int
) -> list[tuple[int, int, int]]:
    subdiv = cv2.Subdiv2D((0, 0, width, height))
    positions = np.array([[node["x"], node["y"]] for node in nodes], dtype=np.float64)
    for x, y in positions:
        safe_x = min(max(float(x), 1e-3), width - 1e-3)
        safe_y = min(max(float(y), 1e-3), height - 1e-3)
        subdiv.insert((safe_x, safe_y))

    triangles: set[tuple[int, int, int]] = set()
    tolerance = max(2.0, max(width, height) * 1e-4)
    for raw in subdiv.getTriangleList():
        vertices = np.asarray(raw, dtype=np.float64).reshape(3, 2)
        if np.any(vertices[:, 0] < 0) or np.any(vertices[:, 0] >= width):
            continue
        if np.any(vertices[:, 1] < 0) or np.any(vertices[:, 1] >= height):
            continue
        indices: list[int] = []
        for vertex in vertices:
            distances = np.linalg.norm(positions - vertex, axis=1)
            nearest = int(np.argmin(distances))
            if float(distances[nearest]) > tolerance:
                indices = []
                break
            indices.append(nearest)
        if len(set(indices)) == 3:
            triangles.add(tuple(sorted(indices)))
    if not triangles:
        raise RuntimeError("Delaunay 삼각형을 생성하지 못했습니다. 별 좌표 분포를 확인해주세요.")
    return sorted(triangles)


def distance(first: dict[str, Any], second: dict[str, Any]) -> float:
    return math.hypot(second["x"] - first["x"], second["y"] - first["y"])


def make_graph(
    nodes: list[dict[str, Any]],
    triangle_indices: list[tuple[int, int, int]],
    width: int,
    height: int,
    max_edge_factor: float,
    keep_all_edges: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    if max_edge_factor <= 0:
        raise ValueError("max-edge-factor는 0보다 커야 합니다.")
    edge_indices = {
        tuple(sorted(pair))
        for triangle in triangle_indices
        for pair in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[0], triangle[2]))
    }
    edge_lengths = [distance(nodes[a], nodes[b]) for a, b in sorted(edge_indices)]
    median_length = float(np.median(edge_lengths))
    cutoff = math.inf if keep_all_edges else median_length * max_edge_factor
    diagonal = math.hypot(width, height)

    edges: list[dict[str, Any]] = []
    kept_pairs: set[tuple[int, int]] = set()
    for a, b in sorted(edge_indices):
        first, second = nodes[a], nodes[b]
        length = distance(first, second)
        if length > cutoff:
            continue
        kept_pairs.add((a, b))
        angle = math.degrees(math.atan2(second["y"] - first["y"], second["x"] - first["x"]))
        edges.append(
            {
                "edge_id": len(edges) + 1,
                "source_id": first["star_id"],
                "target_id": second["star_id"],
                "length_px": round(length, 6),
                "length_image_diagonal": round(length / diagonal, 8),
                "length_median_ratio": round(length / median_length, 8),
                "angle_degrees": round(angle, 6),
            }
        )

    triangles: list[dict[str, Any]] = []
    for original_id, indices in enumerate(triangle_indices, start=1):
        pairs = {
            tuple(sorted((indices[0], indices[1]))),
            tuple(sorted((indices[1], indices[2]))),
            tuple(sorted((indices[0], indices[2]))),
        }
        if not pairs.issubset(kept_pairs):
            continue
        first, second, third = (nodes[index] for index in indices)
        lengths = sorted((distance(first, second), distance(second, third), distance(first, third)))
        cross = abs(
            (second["x"] - first["x"]) * (third["y"] - first["y"])
            - (second["y"] - first["y"]) * (third["x"] - first["x"])
        )
        longest = lengths[2]
        triangles.append(
            {
                "triangle_id": original_id,
                "star_a_id": first["star_id"],
                "star_b_id": second["star_id"],
                "star_c_id": third["star_id"],
                "short_side_px": round(lengths[0], 6),
                "middle_side_px": round(lengths[1], 6),
                "long_side_px": round(longest, 6),
                "short_long_ratio": round(lengths[0] / longest, 8),
                "middle_long_ratio": round(lengths[1] / longest, 8),
                "area_image_ratio": round((cross / 2) / (width * height), 10),
            }
        )
    stats = {
        "all_delaunay_edges": len(edge_indices),
        "median_edge_length_px": round(median_length, 6),
        "edge_cutoff_px": None if math.isinf(cutoff) else round(cutoff, 6),
    }
    return edges, triangles, stats


def annotate_graph(
    image: np.ndarray,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    label_top: int,
) -> np.ndarray:
    by_id = {node["star_id"]: node for node in nodes}
    overlay = image.copy()
    for edge in edges:
        first = by_id[edge["source_id"]]
        second = by_id[edge["target_id"]]
        cv2.line(
            overlay,
            (round(first["x"]), round(first["y"])),
            (round(second["x"]), round(second["y"])),
            (255, 220, 40),
            2,
            cv2.LINE_AA,
        )
    annotated = cv2.addWeighted(overlay, 0.70, image, 0.30, 0)
    for index, node in enumerate(nodes):
        center = (round(node["x"]), round(node["y"]))
        cv2.circle(annotated, center, 5, (0, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(annotated, center, 8, (0, 90, 255), 1, cv2.LINE_AA)
        if index < label_top:
            cv2.putText(
                annotated,
                str(node["star_id"]),
                (center[0] + 9, center[1] - 9),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
    return annotated


def output_stem(path: Path) -> str:
    stem = path.stem
    return stem[:-6] if stem.endswith("_stars") else stem


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    input_path: Path,
    image_path: Path,
    output_dir: Path,
    image: np.ndarray,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    triangles: list[dict[str, Any]],
    stats: dict[str, Any],
    parameters: dict[str, Any],
    annotated: np.ndarray,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_stem(input_path)
    edge_path = output_dir / f"{stem}_edges.csv"
    triangle_path = output_dir / f"{stem}_triangles.csv"
    json_path = output_dir / f"{stem}_graph.json"
    image_output_path = output_dir / f"{stem}_graph.jpg"
    write_csv(edge_path, edges)
    write_csv(triangle_path, triangles)
    payload = {
        "source_detection": str(input_path.resolve()),
        "image": str(image_path.resolve()),
        "width": image.shape[1],
        "height": image.shape[0],
        "algorithm": "Delaunay triangulation with long-edge pruning",
        "parameters": parameters,
        "statistics": {
            **stats,
            "graph_nodes": len(nodes),
            "kept_edges": len(edges),
            "kept_triangles": len(triangles),
        },
        "nodes": nodes,
        "edges": edges,
        "triangles": triangles,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_image(image_output_path, annotated)
    return {
        "edges_csv": edge_path,
        "triangles_csv": triangle_path,
        "graph_json": json_path,
        "graph_image": image_output_path,
    }


def main() -> None:
    args = parse_args()
    input_path = args.stars.resolve()
    image_override = args.image.resolve() if args.image else None
    stars, image_path, expected_width, expected_height = load_stars(input_path, image_override)
    image = read_image(image_path)
    height, width = image.shape[:2]
    if (width, height) != (expected_width, expected_height):
        raise ValueError(
            f"검출 메타데이터({expected_width}x{expected_height})와 원본 이미지({width}x{height}) 크기가 다릅니다."
        )
    nodes = choose_nodes(stars, args.top_stars)
    triangle_indices = delaunay_triangles(nodes, width, height)
    edges, triangles, stats = make_graph(
        nodes,
        triangle_indices,
        width,
        height,
        args.max_edge_factor,
        args.keep_all_edges,
    )
    annotated = annotate_graph(image, nodes, edges, max(0, args.label_top))
    graph_output_dir = args.output_dir.resolve() / output_stem(input_path)
    paths = write_outputs(
        input_path,
        image_path,
        graph_output_dir,
        image,
        nodes,
        edges,
        triangles,
        stats,
        {
            "requested_top_stars": args.top_stars,
            "max_edge_factor": args.max_edge_factor,
            "keep_all_edges": args.keep_all_edges,
        },
        annotated,
    )

    print(f"입력 별 후보: {len(stars):,}개")
    print(f"그래프 노드: {len(nodes):,}개")
    print(f"Delaunay 전체 간선: {stats['all_delaunay_edges']:,}개")
    print(f"유지한 간선: {len(edges):,}개")
    print(f"유지한 삼각형: {len(triangles):,}개")
    print(f"간선 길이 중앙값: {stats['median_edge_length_px']:,.2f}px")
    if stats["edge_cutoff_px"] is not None:
        print(f"긴 간선 제거 기준: {stats['edge_cutoff_px']:,.2f}px")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
