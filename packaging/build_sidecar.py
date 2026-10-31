"""Build the Bellows core sidecar with PyInstaller.

Usage (repo root): python3 packaging/build_sidecar.py

The resulting executable is copied to the Tauri `externalBin` location with the
Rust target triple suffix so `tauri build` can pick it up.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "packaging" / "build" / "dist"


def host_triple() -> str:
    if sys.platform == "win32":
        return "x86_64-pc-windows-msvc"
    if sys.platform == "darwin":
        machine = platform.machine().lower()
        return "aarch64-apple-darwin" if machine in {"arm64", "aarch64"} else "x86_64-apple-darwin"
    machine = platform.machine().lower()
    return (
        "aarch64-unknown-linux-gnu"
        if machine in {"arm64", "aarch64"}
        else "x86_64-unknown-linux-gnu"
    )


def exe_suffix() -> str:
    return ".exe" if sys.platform == "win32" else ""


def main() -> None:
    web_dist = ROOT / "apps" / "web" / "dist"
    if not (web_dist / "index.html").exists():
        raise SystemExit("apps/web/dist is missing; run `npm run build` in apps/web first")

    DIST.mkdir(parents=True, exist_ok=True)
    add_data = f"{web_dist}{os.pathsep}web/dist"
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "bellows-core",
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "packaging" / "build" / "work"),
        "--specpath",
        str(ROOT / "packaging" / "build"),
        "--paths",
        str(ROOT / "apps" / "core"),
        "--add-data",
        add_data,
        "--collect-submodules",
        "uvicorn",
        "--hidden-import",
        "bellows_core",
        str(ROOT / "packaging" / "sidecar_entry.py"),
    ]
    subprocess.run(args, check=True, cwd=ROOT)

    built = DIST / f"bellows-core{exe_suffix()}"
    target_dir = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"bellows-core-{host_triple()}{exe_suffix()}"
    shutil.copy2(built, target)
    print(f"sidecar copied to {target}")


if __name__ == "__main__":
    main()
