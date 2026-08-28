"""Detect point-like star candidates in a smartphone night-sky image."""

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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "star_detection"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Input night-sky image")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="사진 이름별 하위 폴더를 생성할 결과 상위 폴더",
    )
    parser.add_argument("--max-dimension", type=int, default=1920)
    parser.add_argument("--threshold-sigma", type=float, default=6.0)
    parser.add_argument("--percentile", type=float, default=99.7)
    parser.add_argument("--min-area", type=int, default=1)
    parser.add_argument("--max-area", type=int, default=100)
    parser.add_argument("--min-distance", type=float, default=5.0)
    parser.add_argument("--max-stars", type=int, default=250)
    parser.add_argument(
        "--sky-fraction",
        type=float,
        default=0.55,
        help="Analyze this fraction from the top of the image; use 1.0 for the full image",
    )
    parser.add_argument("--minimum-usable-stars", type=int, default=7)
    parser.add_argument("--label-top", type=int, default=50)
    parser.add_argument("--save-debug", action="store_true")
    parser.add_argument(
        "--output-name",
        help="결과 폴더와 파일에 사용할 짧은 이름. 생략하면 입력 이미지 이름을 사용합니다.",
    )
    return parser.parse_args()


def read_image(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"이미지를 읽을 수 없습니다: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    extension = path.suffix.lower() or ".png"
    success, encoded = cv2.imencode(extension, image)
    if not success:
        raise RuntimeError(f"이미지 인코딩에 실패했습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(path)


def resize_for_detection(image: np.ndarray, max_dimension: int) -> tuple[np.ndarray, float]:
    if max_dimension <= 0:
        raise ValueError("max-dimension은 1 이상이어야 합니다.")
    height, width = image.shape[:2]
    scale = min(1.0, max_dimension / max(width, height))
    if scale == 1.0:
        return image.copy(), scale
    resized = cv2.resize(
        image,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def robust_noise_sigma(values: np.ndarray) -> tuple[float, float]:
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return median, max(1e-6, 1.4826 * mad)


def build_detection_map(
    gray: np.ndarray,
    sky_fraction: float,
    threshold_sigma: float,
    percentile: float,
) -> tuple[np.ndarray, np.ndarray, float, int, dict[str, float]]:
    if not 0 < sky_fraction <= 1:
        raise ValueError("sky-fraction은 0보다 크고 1 이하여야 합니다.")
    if not 0 < percentile < 100:
        raise ValueError("percentile은 0보다 크고 100보다 작아야 합니다.")

    gray_float = gray.astype(np.float32)
    fine = cv2.GaussianBlur(gray_float, (0, 0), sigmaX=0.8, sigmaY=0.8)
    background = cv2.GaussianBlur(gray_float, (0, 0), sigmaX=4.0, sigmaY=4.0)
    dog_signed = fine - background
    dog = np.maximum(dog_signed, 0)

    sky_height = max(1, min(gray.shape[0], round(gray.shape[0] * sky_fraction)))
    sky_values = dog_signed[:sky_height].reshape(-1)
    median, noise_sigma = robust_noise_sigma(sky_values)
    positive_values = dog[:sky_height]
    percentile_threshold = float(np.percentile(positive_values, percentile))
    sigma_threshold = median + threshold_sigma * noise_sigma
    threshold = max(0.5, percentile_threshold, sigma_threshold)

    binary = np.zeros_like(gray, dtype=np.uint8)
    binary[:sky_height] = np.where(dog[:sky_height] >= threshold, 255, 0).astype(np.uint8)
    debug = {
        "dog_median": round(median, 6),
        "dog_noise_sigma": round(noise_sigma, 6),
        "percentile_threshold": round(percentile_threshold, 6),
        "sigma_threshold": round(sigma_threshold, 6),
        "threshold": round(threshold, 6),
    }
    return dog, binary, threshold, sky_height, debug


def component_candidates(
    gray: np.ndarray,
    dog: np.ndarray,
    binary: np.ndarray,
    min_area: int,
    max_area: int,
) -> list[dict[str, float]]:
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    candidates: list[dict[str, float]] = []
    for label_id in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[label_id])
        if not min_area <= area <= max_area:
            continue
        if width <= 0 or height <= 0:
            continue
        aspect_ratio = max(width, height) / max(1, min(width, height))
        if aspect_ratio > 3.0 or width > 20 or height > 20:
            continue

        region_labels = labels[y : y + height, x : x + width]
        component_mask = region_labels == label_id
        component_dog = dog[y : y + height, x : x + width]
        weights = np.where(component_mask, component_dog, 0.0)
        weight_sum = float(weights.sum())
        if weight_sum > 0:
            ys, xs = np.indices(weights.shape)
            center_x = x + float((weights * xs).sum() / weight_sum)
            center_y = y + float((weights * ys).sum() / weight_sum)
        else:
            center_x, center_y = (float(value) for value in centroids[label_id])

        peak = float(component_dog[component_mask].max())
        gray_region = gray[y : y + height, x : x + width]
        peak_gray = int(gray_region[component_mask].max())
        radius = math.sqrt(area / math.pi)
        candidates.append(
            {
                "work_x": center_x,
                "work_y": center_y,
                "area_work": float(area),
                "radius_work": radius,
                "peak_gray": float(peak_gray),
                "local_contrast": peak,
                "score": peak * math.sqrt(area),
            }
        )
    return candidates


def non_maximum_suppression(
    candidates: list[dict[str, float]], min_distance: float, max_stars: int
) -> list[dict[str, float]]:
    selected: list[dict[str, float]] = []
    minimum_squared = min_distance * min_distance
    for candidate in sorted(candidates, key=lambda item: item["score"], reverse=True):
        if all(
            (candidate["work_x"] - existing["work_x"]) ** 2
            + (candidate["work_y"] - existing["work_y"]) ** 2
            >= minimum_squared
            for existing in selected
        ):
            selected.append(candidate)
            if len(selected) >= max_stars:
                break
    return selected


def restore_original_coordinates(
    candidates: list[dict[str, float]], scale: float, width: int, height: int
) -> list[dict[str, Any]]:
    stars: list[dict[str, Any]] = []
    for star_id, candidate in enumerate(candidates, start=1):
        x = candidate["work_x"] / scale
        y = candidate["work_y"] / scale
        stars.append(
            {
                "star_id": star_id,
                "x": round(x, 3),
                "y": round(y, 3),
                "x_normalized": round(x / width, 8),
                "y_normalized": round(y / height, 8),
                "area": round(candidate["area_work"] / (scale * scale), 3),
                "radius": round(candidate["radius_work"] / scale, 3),
                "peak_gray": int(candidate["peak_gray"]),
                "local_contrast": round(candidate["local_contrast"], 6),
                "score": round(candidate["score"], 6),
            }
        )
    return stars


def create_annotated_image(
    image: np.ndarray, stars: list[dict[str, Any]], label_top: int
) -> np.ndarray:
    annotated = image.copy()
    for index, star in enumerate(stars):
        center = (round(star["x"]), round(star["y"]))
        radius = max(5, min(18, round(star["radius"] + 4)))
        cv2.circle(annotated, center, radius, (0, 255, 0), 2, cv2.LINE_AA)
        if index < label_top:
            cv2.putText(
                annotated,
                str(star["star_id"]),
                (center[0] + radius + 2, center[1] - radius - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
    return annotated


def write_outputs(
    image_path: Path,
    output_dir: Path,
    image: np.ndarray,
    working_shape: tuple[int, int],
    scale: float,
    sky_height: int,
    stars: list[dict[str, Any]],
    component_candidate_count: int,
    max_stars: int,
    minimum_usable_stars: int,
    debug: dict[str, float],
    annotated: np.ndarray,
    binary: np.ndarray,
    dog: np.ndarray,
    save_debug: bool,
    output_name: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_name or image_path.stem
    csv_path = output_dir / f"{stem}_stars.csv"
    json_path = output_dir / f"{stem}_stars.json"
    annotated_path = output_dir / f"{stem}_annotated.jpg"

    fieldnames = [
        "star_id",
        "x",
        "y",
        "x_normalized",
        "y_normalized",
        "area",
        "radius",
        "peak_gray",
        "local_contrast",
        "score",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(stars)

    original_height, original_width = image.shape[:2]
    metadata = {
        "image": str(image_path.resolve()),
        "width": original_width,
        "height": original_height,
        "working_width": working_shape[1],
        "working_height": working_shape[0],
        "working_scale": round(scale, 8),
        "analyzed_sky_height_original": round(sky_height / scale),
        "detected_stars": len(stars),
        "component_candidates_before_ranking": component_candidate_count,
        "maximum_star_limit_reached": len(stars) >= max_stars,
        "minimum_usable_stars": minimum_usable_stars,
        "usable_for_graph": len(stars) >= minimum_usable_stars,
        "threshold_debug": debug,
        "stars": stars,
    }
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    write_image(annotated_path, annotated)

    paths = {"csv": csv_path, "json": json_path, "annotated": annotated_path}
    if save_debug:
        mask_path = output_dir / f"{stem}_mask.png"
        dog_path = output_dir / f"{stem}_dog.png"
        dog_visual = cv2.normalize(dog, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        write_image(mask_path, binary)
        write_image(dog_path, dog_visual)
        paths.update({"mask": mask_path, "dog": dog_path})
    return paths


def main() -> None:
    args = parse_args()
    if args.min_area < 1 or args.max_area < args.min_area:
        raise ValueError("min-area와 max-area 값을 확인해주세요.")
    if args.max_stars < 1:
        raise ValueError("max-stars는 1 이상이어야 합니다.")

    image_path = args.image.resolve()
    image = read_image(image_path)
    working, scale = resize_for_detection(image, args.max_dimension)
    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    dog, binary, _, sky_height, debug = build_detection_map(
        gray,
        args.sky_fraction,
        args.threshold_sigma,
        args.percentile,
    )
    candidates = component_candidates(
        gray,
        dog,
        binary,
        args.min_area,
        args.max_area,
    )
    selected = non_maximum_suppression(candidates, args.min_distance, args.max_stars)
    stars = restore_original_coordinates(selected, scale, image.shape[1], image.shape[0])
    annotated = create_annotated_image(image, stars, args.label_top)
    output_name = args.output_name or image_path.stem
    image_output_dir = args.output_dir.resolve() / output_name
    paths = write_outputs(
        image_path=image_path,
        output_dir=image_output_dir,
        image=image,
        working_shape=gray.shape,
        scale=scale,
        sky_height=sky_height,
        stars=stars,
        component_candidate_count=len(candidates),
        max_stars=args.max_stars,
        minimum_usable_stars=args.minimum_usable_stars,
        debug=debug,
        annotated=annotated,
        binary=binary,
        dog=dog,
        save_debug=args.save_debug,
        output_name=output_name,
    )

    print(f"검출된 별 후보: {len(stars):,}개")
    if len(stars) == args.max_stars:
        print(f"참고: max-stars 제한({args.max_stars:,}개)에 도달했습니다.")
    print(f"그래프 생성 가능: {'예' if len(stars) >= args.minimum_usable_stars else '아니오'}")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
