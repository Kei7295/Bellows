"""CLI entry point.

Usage:
    python -m bellows_core --data-dir ./data --port 7801

On startup one handshake line is printed to stdout so a Tauri shell can parse
port/token/pid/version without guessing:

    BELLOWS-CORE {"port": 7801, "token": "", "pid": 1234, "version": "0.0.1-beta"}
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

import uvicorn

from . import __version__
from .app import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser(prog="bellows-core", description="Bellows local core")
    parser.add_argument("--data-dir", default=os.environ.get("BELLOWS_DATA_DIR", "./data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BELLOWS_PORT", "7801")))
    parser.add_argument("--token", default=os.environ.get("BELLOWS_TOKEN", ""))
    parser.add_argument("--log-level", default=os.environ.get("BELLOWS_LOG_LEVEL", "info"))
    args = parser.parse_args()

    port = _free_port() if args.port == 0 else args.port
    data_dir = Path(args.data_dir).resolve()
    app, _rt = create_app(data_dir, token=args.token)
    handshake = {"port": port, "token": args.token, "pid": os.getpid(),
                 "version": __version__, "data_dir": str(data_dir)}
    print("BELLOWS-CORE " + json.dumps(handshake, ensure_ascii=False), flush=True)
    print(f"Bellows core listening on http://{args.host}:{port}", flush=True)
    uvicorn.run(app, host=args.host, port=port, log_level=args.log_level)


if __name__ == "__main__":
    main()
