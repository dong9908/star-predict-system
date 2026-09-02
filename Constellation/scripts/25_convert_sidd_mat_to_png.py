"""Convert paired SIDD validation sRGB MATLAB arrays into PNG files."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.io import loadmat, whosmat

from lib.io_utils import configure_utf8_console


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "auxiliary" / "low_light" / "sidd_medium"
DEFAULT_OUTPUT = DEFAULT_INPUT / "extracted_png"
NOISY_FILE = "ValidationNoisyBlocksSrgb.mat"
GT_FILE = "ValidationGtBlocksSrgb.mat"
NOISY_KEY = "ValidationNoisyBlocksSrgb"
GT_KEY = "ValidationGtBlocksSrgb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Convert only the first N pairs for a smoke test; 0 converts all pairs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace PNG files that already exist.",
    )
    return parser.parse_args()


def describe_variable(path: Path, expected_key: str) -> tuple[int, ...]:
    variables = {name: tuple(shape) for name, shape, _ in whosmat(path)}
    if expected_key not in variables:
        raise KeyError(f"Expected variable '{expected_key}' was not found in {path}")
    shape = variables[expected_key]
    if len(shape) != 5 or shape[-1] != 3:
        raise ValueError(f"Unexpected SIDD array shape in {path}: {shape}")
    return shape


def load_array(path: Path, key: str) -> np.ndarray:
    array = loadmat(path, variable_names=[key])[key]
    if array.dtype != np.uint8:
        raise ValueError(f"Expected uint8 data in {path}, got {array.dtype}")
    return array


def write_group(
    mat_path: Path,
    key: str,
    destination: Path,
    pair_limit: int,
    overwrite: bool,
) -> list[tuple[int, int, Path]]:
    print(f"MAT 읽는 중: {mat_path}")
    array = load_array(mat_path, key)
    scenes, blocks = array.shape[:2]
    total = scenes * blocks
    selected = min(pair_limit, total) if pair_limit else total
    destination.mkdir(parents=True, exist_ok=True)

    written: list[tuple[int, int, Path]] = []
    count = 0
    for scene_index in range(scenes):
        for block_index in range(blocks):
            if count >= selected:
                return written
            output_path = destination / f"scene_{scene_index + 1:02d}_block_{block_index + 1:02d}.png"
            if overwrite or not output_path.exists():
                Image.fromarray(array[scene_index, block_index], mode="RGB").save(output_path)
            written.append((scene_index + 1, block_index + 1, output_path))
            count += 1
            if count % 100 == 0 or count == selected:
                print(f"  변환: {count:,}/{selected:,}")
    return written


def write_manifest(
    output_dir: Path,
    noisy_rows: list[tuple[int, int, Path]],
    gt_rows: list[tuple[int, int, Path]],
) -> Path:
    if len(noisy_rows) != len(gt_rows):
        raise ValueError("Noisy and ground-truth output counts do not match.")
    manifest_path = output_dir / "pairs.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("pair_id", "scene", "block", "noisy_png", "ground_truth_png"),
        )
        writer.writeheader()
        for noisy, ground_truth in zip(noisy_rows, gt_rows, strict=True):
            if noisy[:2] != ground_truth[:2]:
                raise ValueError("Noisy and ground-truth pair indices do not match.")
            scene, block, noisy_path = noisy
            _, _, gt_path = ground_truth
            writer.writerow(
                {
                    "pair_id": f"scene_{scene:02d}_block_{block:02d}",
                    "scene": scene,
                    "block": block,
                    "noisy_png": str(noisy_path.resolve()),
                    "ground_truth_png": str(gt_path.resolve()),
                }
            )
    return manifest_path


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.limit < 0:
        raise ValueError("--limit must be 0 or greater.")

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    noisy_path = input_dir / NOISY_FILE
    gt_path = input_dir / GT_FILE
    for path in (noisy_path, gt_path):
        if not path.is_file():
            raise FileNotFoundError(f"SIDD MAT file not found: {path}")

    noisy_shape = describe_variable(noisy_path, NOISY_KEY)
    gt_shape = describe_variable(gt_path, GT_KEY)
    if noisy_shape != gt_shape:
        raise ValueError(f"Noisy/ground-truth shapes differ: {noisy_shape} != {gt_shape}")

    total_pairs = noisy_shape[0] * noisy_shape[1]
    selected_pairs = min(args.limit, total_pairs) if args.limit else total_pairs
    print(f"입력 배열 크기: {noisy_shape}")
    print(f"변환할 이미지 쌍: {selected_pairs:,}/{total_pairs:,}")

    noisy_rows = write_group(
        noisy_path,
        NOISY_KEY,
        output_dir / "noisy",
        args.limit,
        args.overwrite,
    )
    gt_rows = write_group(
        gt_path,
        GT_KEY,
        output_dir / "ground_truth",
        args.limit,
        args.overwrite,
    )
    manifest_path = write_manifest(output_dir, noisy_rows, gt_rows)

    print("SIDD PNG 변환 완료")
    print(f"noisy: {output_dir / 'noisy'} ({len(noisy_rows):,}장)")
    print(f"ground_truth: {output_dir / 'ground_truth'} ({len(gt_rows):,}장)")
    print(f"pairs_csv: {manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("사용자에 의해 변환이 중단됐습니다.", file=sys.stderr)
        raise SystemExit(130)
