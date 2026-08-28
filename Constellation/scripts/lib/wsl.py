"""Windows/WSL interop used by the local Astrometry.net backend."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def run(
    command: list[str],
    *,
    timeout: int = 60,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def run_wsl(
    distribution: str,
    shell_command: str,
    *,
    timeout: int = 60,
    root: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = ["wsl.exe", "-d", distribution]
    if root:
        command.extend(("-u", "root"))
    command.extend(("--", "bash", "-lc", shell_command))
    return run(command, timeout=timeout)


def distributions() -> list[str]:
    if not shutil.which("wsl.exe"):
        return []
    completed = run(["wsl.exe", "--list", "--quiet"])
    return [
        cleaned
        for line in completed.stdout.splitlines()
        if (cleaned := line.replace("\x00", "").strip())
    ]


def command_available(distribution: str, command: str) -> bool:
    if not shutil.which("wsl.exe"):
        return False
    completed = run_wsl(distribution, f"command -v {command}", timeout=20)
    return completed.returncode == 0 and bool(completed.stdout.strip())


def windows_to_wsl(path: Path) -> str:
    windows_path = str(path.resolve())
    match = re.match(r"^([A-Za-z]):\\(.*)$", windows_path)
    if not match:
        raise ValueError(f"지원되지 않는 WSL 경로 형식입니다: {path}")
    drive, remainder = match.groups()
    return f"/mnt/{drive.lower()}/{remainder.replace(chr(92), '/')}"
