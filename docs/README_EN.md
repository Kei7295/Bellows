# Bellows · 风箱

> Protocol in, persona out.

Bellows is a local QQ chat bot workbench. **v0.0.1 BETA** ships a Vue 3 SPA served by a single Python FastAPI process, with a working OneBot v11 reverse WebSocket endpoint. Everything else is explicitly scoped below.

## Quick start

```bash
bash scripts/run.sh
```

Open http://127.0.0.1:7801. On first run the script builds the web UI with npm (if `apps/web/dist/index.html` is missing) and installs `fastapi` / `uvicorn` when needed. Data is stored in `data/` as SQLite (WAL).

Requirements: Python ≥ 3.12, Node.js ≥ 22.18 or ≥ 24.12 (build only). Override with `BELLOWS_PORT` and `BELLOWS_DATA_DIR`; set `BELLOWS_TOKEN` to require Bearer auth on every API except `/api/health`.

## What works (v0.0.1 BETA)

- Desktop-style app shell, collapsible sidebar, light/dark/system themes
- Overview: online instances, today's messages/replies/tokens, 14-day trend, event feed, alerts
- Instance CRUD, connect/disconnect, capability probe, raw config view
- OneBot v11 reverse WS at `ws://127.0.0.1:7801/onebot/v11/ws/<instance_id>` with optional Bearer token
- Message normalization, persistence, `/api/events` push, manual send from console
- Demo pipeline: inbound messages and rule replies every 11–18 seconds, no real QQ needed
- Streams, message history, persona CRUD, provider CRUD, memory browsing
- Plugin list/toggle, read-only marketplace preview
- Logs/audit search, persisted settings
- Seeded SQLite database on first start
- Windows desktop build: Tauri 2 shell with a bundled PyInstaller sidecar, packaged as an NSIS installer in CI

## Desktop (Windows)

Download the `Bellows_0.0.1-beta_x64-setup.exe` from [Releases](https://github.com/Kei7295/Bellows/releases/latest) (or the `bellows-windows-nsis` Actions artifact) and install it. The installer is unsigned, so SmartScreen may warn about an unknown publisher. The shell starts the embedded core on a free localhost port and stores data under `%APPDATA%\dev.bellows.desktop`; Python and Node are not required. macOS/Linux desktop bundles are not provided yet.

## Explicitly not included

- **No real LLM calls** — provider "test" is simulated, replies come from a rule engine
- **No plugin runtime** — toggles only update the database, `reload` is unimplemented
- Reverse WS only; forward WS / HTTP are scaffolds
- No keychain, automatic memory extraction, vector search, MCP or scheduler
- QQ login/QR is handled by NapCat / SnowLuma, never by Bellows

## Connect NapCat / SnowLuma

1. Enable "reverse WebSocket" in the protocol adapter.
2. Use `ws://127.0.0.1:7801/onebot/v11/ws/<instance_id>`; seeded instance `ins_second` uses token `beta-token`.
3. Once connected, the instance becomes online and a log entry appears.
4. Group @-mentions, messages containing "风箱", and private messages trigger rule replies sent back over the same WS as `send_msg`.

Debug without an adapter:

```bash
curl -s -X POST http://127.0.0.1:7801/api/debug/inbound \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"ins_main","text":"风箱，测试一条消息。","sender_name":"probe"}'
```

## Development

```bash
cd apps/core && python3 -m bellows_core --data-dir ../../data --port 7801
cd apps/web && npm run dev
```

Checks: `bash scripts/check.sh` (ruff, pytest, vue-tsc, vite build). See [DEVELOPMENT.md](DEVELOPMENT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [API.md](API.md), [DEPLOYMENT.md](DEPLOYMENT.md), [ONEBOT.md](ONEBOT.md), and [FAQ.md](FAQ.md).

## License

AGPL-3.0. See [LICENSE](../LICENSE). Copyright (C) 2026 Kei7295.
