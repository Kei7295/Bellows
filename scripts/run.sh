#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE="$ROOT/apps/core"
WEB="$ROOT/apps/web"

if [ ! -f "$WEB/dist/index.html" ]; then
  echo "[bellows] building web UI..."
  (cd "$WEB" && npm install --no-audit --no-fund && npm run build)
fi

if ! python3 -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "[bellows] installing Python dependencies..."
  python3 -m pip install -r "$CORE/requirements.txt"
fi

cd "$CORE"
exec python3 -m bellows_core \
  --data-dir "${BELLOWS_DATA_DIR:-$ROOT/data}" \
  --port "${BELLOWS_PORT:-7801}" \
  --token "${BELLOWS_TOKEN:-}" \
  "$@"
