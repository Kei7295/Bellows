#!/usr/bin/env bash
# 本地统一检查入口，与 CI (.github/workflows/ci.yml) 保持一致。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[bellows] ruff check..."
cd "$ROOT" && ruff check apps/core tests

echo "[bellows] ruff format check..."
cd "$ROOT" && ruff format --check apps/core tests

echo "[bellows] pytest..."
cd "$ROOT" && python3 -m pytest tests -q

echo "[bellows] web type-check..."
cd "$ROOT/apps/web" && npm run type-check

echo "[bellows] web build..."
cd "$ROOT/apps/web" && npm run build

echo "[bellows] all checks passed."
