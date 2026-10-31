# 开发指南

## 环境

| 工具 | 版本 |
| --- | --- |
| Python | ≥ 3.12（CI 用 3.12） |
| Node.js | ≥ 22.18 或 ≥ 24.12（CI 用 24） |
| npm | 随 Node 提供 |

不需要数据库服务，也不需要 Docker 即可开发。

## 首次安装

```bash
cd apps/web && npm ci
cd ../../apps/core && python3 -m pip install -r requirements-dev.txt
```

## 两种运行方式

### 一站式（构建 SPA 后由内核托管）

```bash
bash scripts/run.sh
# 打开 http://127.0.0.1:7801
```

`run.sh` 在 `apps/web/dist/index.html` 缺失时自动 `npm install + npm run build`，并按需安装 Python 依赖。

### 分离开发（前端热更新）

```bash
# 终端 1：内核
cd apps/core
python3 -m bellows_core --data-dir ../../data --port 7801

# 终端 2：Vite（/api 与 /onebot 代理到 7801）
cd apps/web
npm run dev
```

Vite 由 `vite.config.ts` 代理，前端地址通常是 `http://127.0.0.1:5173`。

## 检查

```bash
bash scripts/check.sh
```

包含：

- `ruff check apps/core tests`
- `ruff format --check apps/core tests`（修复用 `ruff format apps/core tests`）
- `pytest -q`
- `npm run type-check`
- `npm run build`

## 测试

测试位于 `tests/`，使用 FastAPI `TestClient`，每个用例创建独立临时数据目录，不触碰 `data/`。

```bash
python -m pytest tests -q
python -m pytest tests/test_instances.py -q -k create
```

需要 `httpx`（`requirements-dev.txt` 已包含）。

## 数据与重置

- 数据目录默认 `data/`，可用 `BELLOWS_DATA_DIR` 覆盖。
- 想回到种子数据：停止内核后删除 `data/`（或 `data/data.db*`），重启即重建。
- 端口被占用时：`BELLOWS_PORT=7802 bash scripts/run.sh`，或让内核自动选端口（`--port 0`）。

## 调试技巧

- 看握手行：启动时 stdout 打印 `BELLOWS-CORE {...}`，包含实际端口、pid、版本。
- 不接协议端注入消息：

```bash
curl -s -X POST http://127.0.0.1:7801/api/debug/inbound \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"ins_main","text":"风箱，测试一条消息。"}'
```

- 事件流调试：`wscat` 或用浏览器 DevTools 观察 `/api/events`。
- 设置 `--token test-token` 后，所有 API 需带 `Authorization: Bearer test-token`。

## 常见坑

| 现象 | 原因 / 处理 |
| --- | --- |
| `npm ci` 失败 | Node 版本过低（`fuxsto-design` engines 提示），升级到 ≥ 22.18 |
| 内核启动报端口占用 | 改 `BELLOWS_PORT` 或先结束旧进程 |
| 前端空白 | 未构建 dist 且未跑 Vite；执行 `npm run build` 或 `npm run dev` |
| 修改前端后 7801 不变 | 7801 提供的是构建产物；开发请用 Vite 或重新 build |
| OneBot 一直 offline | 协议端需要使用反向 WS 并连到正确实例 ID |
