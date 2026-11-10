"""Build the Bellows core sidecar with PyInstaller.

Usage (repo root): python3 packaging/build_sidecar.py

The resulting executable is copied to the Tauri `externalBin` location with the
Rust target triple suffix so `tauri build` can pick it up.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "packaging" / "build" / "dist"


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
        "--onedir",
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

    # onedir: no per-launch extraction, so the desktop app starts in ~1s instead
    # of paying the onefile unpack cost on every boot.
    built_dir = DIST / "bellows-core"
    built_exe = built_dir / f"bellows-core{exe_suffix()}"
    if not built_exe.exists():
        raise SystemExit(f"sidecar build output missing: {built_exe}")

    target_dir = ROOT / "apps" / "desktop" / "src-tauri" / "sidecar"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(built_dir, target_dir)

    # Drop stale onefile artefacts from older builds.
    legacy = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
    if legacy.exists():
        shutil.rmtree(legacy)

    print(f"sidecar copied to {target_dir} ({built_exe.stat().st_size // 1024} KiB exe)")


if __name__ == "__main__":
    main()
