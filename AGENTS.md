# AGENTS.md

面向在本仓库工作的 AI 编码代理的约定。人类贡献者请读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 项目事实

- Bellows（风箱）v0.0.1 BETA：Vue 3 前端 + Python FastAPI 内核，单进程托管 SPA。
- 目录：`apps/web`（Vue 3 + TS + Vite + Tailwind v4 + fuxsto-design），`apps/core/bellows_core`（db / onebot / demo / events / api / app），`scripts/`，`docs/`。
- 运行：`bash scripts/run.sh`，默认 `http://127.0.0.1:7801`，数据写入 `data/`。
- 唯一免鉴权 API 是 `/api/health`；设置 `--token` 后其余 `/api` 需 `Authorization: Bearer`。

## 修改规则

1. 不要新增未在 README 计划中的能力；BETA 边界见 README「明确未完成 / 未验证」。
2. 不要为了「像完整项目」而创建空壳模块、占位实现或无人调用的抽象。
3. API 变更同步 `docs/API.md`、`apps/web/src/api.ts`、`apps/web/src/types.ts`。
4. 数据层只通过 `apps/core/bellows_core/db.py`；不要在路由里直接拼 SQL 初始化表。
5. 前端沿用现有组件与设计 token，不引入新的 UI 框架或状态库。
6. 不要提交 `node_modules/`、`apps/web/dist/`、`data/`、Token、真实聊天记录。

## 必须执行的检查

```bash
bash scripts/check.sh
```

等价于：`ruff check` / `ruff format --check` / `pytest`（apps/core），`npm run type-check` / `npm run build`（apps/web）。

## 文档更新

- 行为变化：README 能力表 + `CHANGELOG.md`。
- 新命令或部署方式：`docs/DEVELOPMENT.md` / `docs/DEPLOYMENT.md`。
- 安全相关：`SECURITY.md`。

## 许可

所有改动以 AGPL-3.0 授权。
