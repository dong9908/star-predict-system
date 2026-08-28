"""Convert the downloaded Gaia DR3 VOTable archive to a UTF-8 CSV file."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

from astropy.io.votable import parse_single_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT / "a5af0177-a02b-11f1-beb9-bc97e148b76b-O-result.vot.gz"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "reference" / "gaia_dr3_g10.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a compressed Gaia VOTable result to CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input .vot.gz file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Gaia VOTable 파일을 찾을 수 없습니다: {input_path}")
    if input_path == output_path:
        raise ValueError("입력 파일과 출력 파일 경로는 달라야 합니다.")

    print(f"입력 파일: {input_path}")
    print("VOTable을 읽는 중입니다. 파일 크기에 따라 잠시 걸릴 수 있습니다.")

    with gzip.open(input_path, "rb") as compressed_file:
        table = parse_single_table(compressed_file).to_table(use_names_over_ids=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.write(output_path, format="ascii.csv", overwrite=True)

    print(f"변환 완료: {output_path}")
    print(f"데이터 행 수: {len(table):,}")
    print(f"열 수: {len(table.colnames):,}")
    print(f"열 이름: {', '.join(table.colnames)}")


if __name__ == "__main__":
    main()
