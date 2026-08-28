"""Validate local catalogues and cross-references used by recognition pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "data" / "results" / "reference_validation.json"

PATHS = {
    "hyg": PROJECT_ROOT / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv",
    "gaia": PROJECT_ROOT / "data" / "reference" / "gaia_dr3_g10.csv",
    "boundaries": PROJECT_ROOT / "data" / "reference" / "constellation_boundaries_j2000.csv",
    "stellarium_index": PROJECT_ROOT / "data" / "reference" / "stellarium" / "western" / "index.json",
    "stellarium_description": PROJECT_ROOT / "data" / "reference" / "stellarium" / "western" / "description.md",
    "smartphone_dataset": PROJECT_ROOT / "data" / "photo" / "AstroSmartphoneDataset",
    "constellation_dataset": PROJECT_ROOT / "data" / "photo" / "ConstellationDataset",
}

HYG_REQUIRED = {"hip", "ra", "dec", "mag", "con", "proper"}
GAIA_REQUIRED = {
    "source_id",
    "designation",
    "ra",
    "dec",
    "ref_epoch",
    "pmra",
    "pmdec",
    "parallax",
    "phot_g_mean_mag",
    "phot_bp_mean_mag",
    "phot_rp_mean_mag",
    "bp_rp",
}
BOUNDARY_REQUIRED = {"RAJ2000", "DEJ2000", "cst", "type"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def normalize_constellation_code(value: Any) -> str | None:
    if pd.isna(value):
        return None
    code = str(value).strip().upper()
    if not code:
        return None
    if code in {"SER1", "SER2"}:
        return "SER"
    return code


def add_issue(report: dict[str, Any], level: str, message: str) -> None:
    report[level].append(message)


def validate_paths(report: dict[str, Any]) -> bool:
    all_present = True
    report["files"] = {}
    for name, path in PATHS.items():
        exists = path.is_dir() if name.endswith("dataset") else path.is_file()
        report["files"][name] = {"path": str(path), "exists": exists}
        if not exists:
            add_issue(report, "errors", f"필수 경로가 없습니다: {path}")
            all_present = False
    return all_present


def validate_hyg(report: dict[str, Any]) -> tuple[pd.DataFrame, set[int], set[str]]:
    path = PATHS["hyg"]
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing_columns = sorted(HYG_REQUIRED - set(header))
    if missing_columns:
        add_issue(report, "errors", f"HYG 필수 열 누락: {missing_columns}")
        return pd.DataFrame(), set(), set()

    frame = pd.read_csv(path, usecols=sorted(HYG_REQUIRED), low_memory=False)
    numeric_ra = pd.to_numeric(frame["ra"], errors="coerce")
    numeric_dec = pd.to_numeric(frame["dec"], errors="coerce")
    numeric_mag = pd.to_numeric(frame["mag"], errors="coerce")
    hip_values = pd.to_numeric(frame["hip"], errors="coerce").dropna().astype("int64")
    hip_set = set(hip_values.tolist())
    normalized_codes = frame["con"].map(normalize_constellation_code).dropna()
    codes = {str(code) for code in normalized_codes}

    invalid_coordinates = int(
        (~numeric_ra.between(0, 24, inclusive="both") | ~numeric_dec.between(-90, 90, inclusive="both")).sum()
    )
    duplicate_hips = int(hip_values.duplicated().sum())
    report["hyg"] = {
        "rows": len(frame),
        "columns": len(header),
        "hip_count": len(hip_set),
        "duplicate_hip_rows": duplicate_hips,
        "constellation_code_count": len(codes),
        "invalid_coordinate_rows": invalid_coordinates,
        "magnitude_missing_rows": int(numeric_mag.isna().sum()),
    }
    if invalid_coordinates:
        add_issue(report, "errors", f"HYG 좌표 범위를 벗어난 행: {invalid_coordinates}")
    if duplicate_hips:
        add_issue(report, "warnings", f"HYG 중복 HIP 행: {duplicate_hips}")
    return frame, hip_set, codes


def validate_gaia(report: dict[str, Any]) -> set[str]:
    path = PATHS["gaia"]
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing_columns = sorted(GAIA_REQUIRED - set(header))
    if missing_columns:
        add_issue(report, "errors", f"Gaia 필수 열 누락: {missing_columns}")
        return set(header)

    frame = pd.read_csv(path, usecols=header, low_memory=False)
    ra = pd.to_numeric(frame["ra"], errors="coerce")
    dec = pd.to_numeric(frame["dec"], errors="coerce")
    mag = pd.to_numeric(frame["phot_g_mean_mag"], errors="coerce")
    invalid_coordinates = int(
        (~ra.between(0, 360, inclusive="both") | ~dec.between(-90, 90, inclusive="both")).sum()
    )
    duplicate_sources = int(frame["source_id"].duplicated().sum())
    brighter_than_limit = int((mag <= 10).sum())
    report["gaia"] = {
        "rows": len(frame),
        "columns": len(header),
        "duplicate_source_ids": duplicate_sources,
        "invalid_coordinate_rows": invalid_coordinates,
        "g_magnitude_missing_rows": int(mag.isna().sum()),
        "g_magnitude_min": float(mag.min()),
        "g_magnitude_max": float(mag.max()),
        "rows_at_or_brighter_than_g10": brighter_than_limit,
    }
    if invalid_coordinates:
        add_issue(report, "errors", f"Gaia 좌표 범위를 벗어난 행: {invalid_coordinates}")
    if duplicate_sources:
        add_issue(report, "errors", f"Gaia source_id 중복 행: {duplicate_sources}")
    if brighter_than_limit != len(frame):
        add_issue(report, "warnings", "Gaia 파일에 G>10인 행 또는 밝기 결측치가 있습니다.")
    return set(header)


def validate_boundaries(report: dict[str, Any]) -> set[str]:
    path = PATHS["boundaries"]
    frame = pd.read_csv(path)
    missing_columns = sorted(BOUNDARY_REQUIRED - set(frame.columns))
    if missing_columns:
        add_issue(report, "errors", f"경계 데이터 필수 열 누락: {missing_columns}")
        return set()

    ra = pd.to_numeric(frame["RAJ2000"], errors="coerce")
    dec = pd.to_numeric(frame["DEJ2000"], errors="coerce")
    raw_codes = {str(value).strip().upper() for value in frame["cst"].dropna()}
    codes = {normalize_constellation_code(value) for value in raw_codes}
    codes.discard(None)
    invalid_coordinates = int(
        (~ra.between(0, 360, inclusive="both") | ~dec.between(-90, 90, inclusive="both")).sum()
    )
    report["boundaries"] = {
        "rows": len(frame),
        "raw_code_count": len(raw_codes),
        "normalized_code_count": len(codes),
        "serpens_split_present": {"SER1", "SER2"}.issubset(raw_codes),
        "point_types": sorted(str(value) for value in frame["type"].dropna().unique()),
        "invalid_coordinate_rows": invalid_coordinates,
    }
    if len(codes) != 88:
        add_issue(report, "errors", f"정규화된 IAU 경계 코드가 88개가 아닙니다: {len(codes)}")
    if invalid_coordinates:
        add_issue(report, "errors", f"경계 좌표 범위를 벗어난 행: {invalid_coordinates}")
    return {str(code) for code in codes}


def validate_stellarium(report: dict[str, Any], hyg_hips: set[int]) -> tuple[set[str], set[int]]:
    path = PATHS["stellarium_index"]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    constellations = data.get("constellations", [])
    codes: set[str] = set()
    referenced_hips: set[int] = set()
    line_paths = 0
    malformed_lines = 0

    for constellation in constellations:
        code = normalize_constellation_code(constellation.get("iau"))
        if code:
            codes.add(code)
        for line in constellation.get("lines", []):
            line_paths += 1
            if not isinstance(line, list):
                malformed_lines += 1
                continue
            referenced_hips.update(value for value in line if isinstance(value, int))

    missing_hyg_hips = sorted(referenced_hips - hyg_hips)
    coverage = (
        100.0 * (len(referenced_hips) - len(missing_hyg_hips)) / len(referenced_hips)
        if referenced_hips
        else 0.0
    )
    report["stellarium"] = {
        "culture_id": data.get("id"),
        "constellations": len(constellations),
        "iau_code_count": len(codes),
        "line_paths": line_paths,
        "unique_referenced_hips": len(referenced_hips),
        "hips_found_in_hyg": len(referenced_hips) - len(missing_hyg_hips),
        "hip_coverage_percent": round(coverage, 3),
        "missing_hyg_hips": missing_hyg_hips,
        "malformed_line_paths": malformed_lines,
        "description_present": PATHS["stellarium_description"].is_file(),
    }
    if len(constellations) != 88 or len(codes) != 88:
        add_issue(report, "errors", "Stellarium Western 별자리 또는 IAU 코드가 88개가 아닙니다.")
    if malformed_lines:
        add_issue(report, "errors", f"Stellarium 잘못된 연결선 경로: {malformed_lines}")
    if missing_hyg_hips:
        add_issue(report, "warnings", f"HYG에서 찾지 못한 Stellarium HIP: {len(missing_hyg_hips)}개")
    return codes, referenced_hips


def validate_image_datasets(report: dict[str, Any]) -> None:
    smartphone_root = PATHS["smartphone_dataset"]
    smartphone_images = [
        path
        for path in smartphone_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    constellation_root = PATHS["constellation_dataset"]
    stars = {path.stem for path in (constellation_root / "stars").glob("*.png")}
    labels = {path.stem for path in (constellation_root / "labels").glob("*.png")}
    names_path = constellation_root / "constellation names.txt"
    names = [
        line.strip()
        for line in names_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if line.strip()
    ]
    report["image_datasets"] = {
        "smartphone_images": len(smartphone_images),
        "constellation_star_images": len(stars),
        "constellation_label_images": len(labels),
        "constellation_image_pairs": len(stars & labels),
        "star_images_without_label": sorted(stars - labels),
        "label_images_without_star": sorted(labels - stars),
        "constellation_names": len(names),
    }
    if stars != labels:
        add_issue(report, "errors", "별자리 기준 이미지와 연결선 이미지의 번호가 일치하지 않습니다.")


def compare_constellation_codes(
    report: dict[str, Any], hyg_codes: set[str], boundary_codes: set[str], stellarium_codes: set[str]
) -> None:
    union = hyg_codes | boundary_codes | stellarium_codes
    report["constellation_code_comparison"] = {
        "union_count": len(union),
        "hyg_only": sorted(hyg_codes - boundary_codes - stellarium_codes),
        "missing_from_hyg": sorted((boundary_codes | stellarium_codes) - hyg_codes),
        "missing_from_boundaries": sorted((hyg_codes | stellarium_codes) - boundary_codes),
        "missing_from_stellarium": sorted((hyg_codes | boundary_codes) - stellarium_codes),
    }
    if boundary_codes != stellarium_codes:
        add_issue(report, "errors", "IAU 경계 코드와 Stellarium Western 코드가 일치하지 않습니다.")
    if not boundary_codes.issubset(hyg_codes):
        add_issue(report, "warnings", "HYG에 일부 IAU 별자리 코드가 없습니다.")


def main() -> None:
    args = parse_args()
    report: dict[str, Any] = {"status": "unknown", "errors": [], "warnings": []}
    if not validate_paths(report):
        report["status"] = "failed"
    else:
        _, hyg_hips, hyg_codes = validate_hyg(report)
        validate_gaia(report)
        boundary_codes = validate_boundaries(report)
        stellarium_codes, _ = validate_stellarium(report, hyg_hips)
        validate_image_datasets(report)
        compare_constellation_codes(report, hyg_codes, boundary_codes, stellarium_codes)
        report["status"] = "failed" if report["errors"] else "passed_with_warnings" if report["warnings"] else "passed"

    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"검증 상태: {report['status']}")
    print(f"오류: {len(report['errors'])}개, 경고: {len(report['warnings'])}개")
    for message in report["errors"]:
        print(f"[ERROR] {message}")
    for message in report["warnings"]:
        print(f"[WARN] {message}")
    print(f"보고서: {report_path}")

    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
