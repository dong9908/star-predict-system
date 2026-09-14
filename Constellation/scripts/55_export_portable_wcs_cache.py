"""Export only verified WCS headers into a small SHA-256 deployment cache."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_plate_solving" / "plate_solve_results.csv"
DEFAULT_OUTPUT = PROJECT_ROOT.parent / "deploy" / "wcs-cache"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, dict[str, str]] = {}
    skipped = 0

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("status") not in {"success", "cached_success"}:
                continue
            source = Path(row.get("source_path", ""))
            wcs = Path(row.get("wcs_path", ""))
            if not source.is_file() or not wcs.is_file():
                skipped += 1
                continue
            digest = file_hash(source)
            target = output_dir / f"{digest}.wcs"
            if not target.is_file() or target.stat().st_size != wcs.stat().st_size:
                shutil.copy2(wcs, target)
            exported[digest] = {"filename": source.name, "wcs": target.name}

    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(input_path),
        "count": len(exported),
        "skipped": skipped,
        "entries": exported,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"WCS cache exported: {len(exported)}")
    print(f"Skipped: {skipped}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
