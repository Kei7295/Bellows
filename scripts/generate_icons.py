"""Generate the Bellows icon set from the master artwork.

Usage (repo root): python3 scripts/generate_icons.py

`assets/app-icon.png` is the 1024×1024 master (designed in the trae-design
canvas). This script only derives the platform-specific sizes so every target
stays pixel-consistent.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "assets" / "app-icon.png"
ICON_DIR = ROOT / "apps" / "desktop" / "src-tauri" / "icons"
WEB_ICON = ROOT / "apps" / "web" / "public" / "icon.png"

PNG_SIZES = {
    "32x32.png": 32,
    "128x128.png": 128,
    "128x128@2x.png": 256,
    "256x256.png": 256,
    "512x512.png": 512,
    "icon.png": 1024,
}

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not MASTER.exists():
        raise SystemExit(f"missing master artwork: {MASTER}")
    with Image.open(MASTER) as source:
        master = source.convert("RGBA")

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for name, size in PNG_SIZES.items():
        master.resize((size, size), Image.LANCZOS).save(ICON_DIR / name, optimize=True)

    master.save(ICON_DIR / "icon.ico", sizes=ICO_SIZES)

    WEB_ICON.parent.mkdir(parents=True, exist_ok=True)
    master.resize((512, 512), Image.LANCZOS).save(WEB_ICON, optimize=True)

    print(f"icons written to {ICON_DIR} and {WEB_ICON}")


if __name__ == "__main__":
    sys.exit(main())
