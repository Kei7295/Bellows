#!/usr/bin/env bash
set -euo pipefail

cd /app/apps/core
exec python3 -m bellows_core \
  --host "${BELLOWS_HOST:-0.0.0.0}" \
  --port "${BELLOWS_PORT:-7801}" \
  --data-dir "${BELLOWS_DATA_DIR:-/data}" \
  --token "${BELLOWS_TOKEN:-}" \
  --log-level "${BELLOWS_LOG_LEVEL:-info}" \
  "$@"
