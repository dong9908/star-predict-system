"""Convert VizieR's VOTable-with-CSV payload into a plain CSV file."""

from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "vizier_votable.tsv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "reference" / "constellation_boundaries_j2000.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"VizieR TSV 파일을 찾을 수 없습니다: {input_path}")
    if input_path == output_path:
        raise ValueError("입력 파일과 출력 파일 경로는 달라야 합니다.")

    text = input_path.read_text(encoding="utf-8-sig")
    match = re.search(r"<!\[CDATA\[(.*?)\]\]>", text, flags=re.DOTALL)
    if not match:
        raise RuntimeError("VOTable 내부의 CSV 데이터를 찾지 못했습니다.")

    lines = [line for line in match.group(1).strip().splitlines() if line.strip()]
    if len(lines) < 4:
        raise RuntimeError("VizieR 데이터 행이 예상보다 적습니다.")

    header = [value.strip() for value in next(csv.reader([lines[0]], delimiter=";"))]
    rows = [
        [value.strip() for value in row]
        for row in csv.reader(lines[3:], delimiter=";")
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"변환 완료: {output_path}")
    print(f"데이터 행 수: {len(rows):,}")


if __name__ == "__main__":
    main()
