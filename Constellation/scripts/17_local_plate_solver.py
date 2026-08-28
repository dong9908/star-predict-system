"""Check, install, and test the WSL Astrometry.net local plate solver."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.io_utils import write_json
from lib.wsl import distributions, run_wsl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATE_SCRIPT = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "results" / "local_plate_solver" / "environment.json"
INDEX_PACKAGE = "astrometry-data-tycho2-10-19-littleendian"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", default="Ubuntu")
    parser.add_argument("--check", action="store_true", help="환경 점검(기본 동작)")
    parser.add_argument("--install", action="store_true", help="Astrometry.net과 광각 인덱스 설치")
    parser.add_argument("--test", type=Path, help="07단계를 WSL 로컬 전용으로 실행할 사진")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def check_environment(distribution: str) -> dict[str, Any]:
    installed_distributions = distributions()
    exists = distribution.lower() in {name.lower() for name in installed_distributions}
    solver = run_wsl(distribution, "command -v solve-field && solve-field --version", timeout=30) if exists else None
    indexes = run_wsl(
        distribution,
        f"find /usr/share/astrometry -maxdepth 1 -type f -name 'index-*.fits' -printf '%f %s\\n' | sort",
        timeout=30,
    ) if exists else None
    index_rows = []
    if indexes and indexes.returncode == 0:
        for line in indexes.stdout.splitlines():
            parts = line.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                index_rows.append({"name": parts[0], "bytes": int(parts[1])})
    return {
        "wsl_executable": "wsl.exe" if installed_distributions else None,
        "distributions": installed_distributions,
        "selected_distribution": distribution,
        "distribution_available": exists,
        "solve_field_available": bool(solver and solver.returncode == 0),
        "solve_field_output": solver.stdout.strip() if solver else "",
        "index_count": len(index_rows),
        "index_bytes": sum(row["bytes"] for row in index_rows),
        "indexes": index_rows,
        "ready": bool(solver and solver.returncode == 0 and index_rows),
    }


def install(distribution: str) -> None:
    print(f"{distribution}에 Astrometry.net과 광각 인덱스를 설치합니다.")
    command = (
        "export DEBIAN_FRONTEND=noninteractive; "
        "apt-get update && "
        f"apt-get install -y astrometry.net {INDEX_PACKAGE}"
    )
    completed = run_wsl(distribution, command, timeout=1800, root=True)
    if completed.stdout:
        print(completed.stdout)
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)


def test_image(image: Path, distribution: str, timeout_seconds: int) -> int:
    image = image.resolve()
    if not image.is_file():
        raise FileNotFoundError(f"테스트 이미지를 찾을 수 없습니다: {image}")
    command = [
        sys.executable,
        str(PLATE_SCRIPT),
        str(image),
        "--backend", "local",
        "--wsl-distribution", distribution,
        "--timeout-seconds", str(timeout_seconds),
        "--downsample", "4",
        "--scale-units", "degwidth",
        "--scale-lower", "40",
        "--scale-upper", "110",
        "--force",
    ]
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


def main() -> None:
    args = parse_args()
    if args.install:
        install(args.distribution)
    status = check_environment(args.distribution)
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    write_json(report, status)
    print(f"WSL 배포판: {args.distribution} - {'사용 가능' if status['distribution_available'] else '없음'}")
    print(f"solve-field: {'사용 가능' if status['solve_field_available'] else '없음'}")
    print(f"광각 인덱스: {status['index_count']}개 ({status['index_bytes'] / 1024 / 1024:.1f} MiB)")
    print(f"로컬 Plate Solver 준비: {'완료' if status['ready'] else '미완료'}")
    print(f"report: {report}")
    if args.test:
        if not status["ready"]:
            raise SystemExit("로컬 Plate Solver 환경이 준비되지 않았습니다.")
        raise SystemExit(test_image(args.test, args.distribution, args.timeout_seconds))


if __name__ == "__main__":
    main()
