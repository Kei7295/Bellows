# CLAUDE.md

本仓库的代理约定集中在 [AGENTS.md](AGENTS.md)，此处只保留最常用的事实。

- 单命令启动：`bash scripts/run.sh` → http://127.0.0.1:7801
- 检查：`bash scripts/check.sh`（ruff + pytest + vue-tsc + vite build）
- 内核：`apps/core/bellows_core`，入口 `python3 -m bellows_core --data-dir ../../data --port 7801`
- 前端：`apps/web`，`npm run dev` / `npm run build`
- 鉴权：`--token` 时除 `/api/health` 外需 Bearer；OneBot WS 用实例的 `access_token`
- 不要提交 `node_modules/`、`apps/web/dist/`、`data/`、任何凭据

改动前先读 README 的能力边界表；不要实现「未完成清单」中的假功能。
