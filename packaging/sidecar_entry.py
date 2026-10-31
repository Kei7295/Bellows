"""PyInstaller entry point for the Bellows core sidecar."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled_web = bundle_root / "web" / "dist"
        if bundled_web.exists():
            os.environ.setdefault("BELLOWS_WEB_DIST", str(bundled_web))

    from bellows_core.__main__ import main as core_main

    core_main()


if __name__ == "__main__":
    main()
