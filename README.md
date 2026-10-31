# Bellows · 风箱

> 协议进风，人格出火。

Bellows（风箱）是一个本地运行的 QQ 聊天 BOT 工作台。本次交付为 **v0.0.1 BETA**：Vue 3 前端构建为静态资源，由 Python FastAPI 单进程托管；OneBot v11 反向 WebSocket 接入可用，其余能力按下方边界表标注。

## 快速开始（单命令）

```bash
bash scripts/run.sh
```

打开 http://127.0.0.1:7801 。首次运行会自动执行：

1. `apps/web` 下 `npm install` + `npm run build`（若 `dist/index.html` 不存在）；
2. 安装 Python 依赖 `fastapi` / `uvicorn`（若缺失）；
3. 启动内核，数据写入 `data/`（SQLite WAL）。

环境要求：

- Node.js ≥ 22.18 或 ≥ 24.12（仅构建前端需要；`fuxsto-design` 有 engines 提示）
- Python ≥ 3.12
- 端口默认 `7801`，可用 `BELLOWS_PORT` 覆盖；数据目录可用 `BELLOWS_DATA_DIR` 覆盖

前台运行示例：

```bash
BELLOWS_PORT=7801 bash scripts/run.sh
```

## 已实现 / 可用（v0.0.1 BETA）

| 能力 | 状态 |
| --- | --- |
| 桌面式 App Shell（自定义标题栏、可折叠侧栏、亮/暗/跟随系统） | 可用 |
| 总览：在线实例、今日消息/回复/Token、14 天趋势、事件流、告警 | 可用 |
| 实例 CRUD、连接/断开、能力探测、原始配置查看 | 可用 |
| OneBot v11 反向 WS 服务端 `ws://127.0.0.1:7801/onebot/v11/ws/<instance_id>`，Bearer Token 校验 | 可用 |
| 消息归一化、落库、`/api/events` 实时推送、消息控制台人工发送 | 可用 |
| 演示管线：每 11–18 秒生成入站消息与规则回复（无需真实 QQ） | 可用 |
| 会话列表、消息检索、人格 CRUD、Provider CRUD、记忆浏览/删除 | 可用 |
| 插件列表与开关、只读插件市场预览 | 状态可落库；运行时不加载 |
| 日志 / 审计检索、设置持久化 | 可用 |
| SQLite 持久化与首次种子数据（3 实例、6 会话、30 消息、14 天统计等） | 可用 |

## 明确未完成 / 未验证（诚实边界）

| 项 | 说明 |
| --- | --- |
| Tauri 桌面壳 | **未包含**。仓库内没有 `apps/desktop` 与 Rust 代码，也没有桌面安装包；本次以浏览器 SPA + Python core 交付。 |
| 真实 LLM 推理 | **未接入**。Provider 的「测试」为模拟探测（返回 `mode: "simulated"`）；回复由规则引擎生成。 |
| 插件运行时 | **未实现**。开关只更新数据库与审计日志，`reload` 返回未实现；市场为只读预览，不能安装。 |
| 正向 WS / HTTP 接入 | 仅 scaffold 与规划；BETA 只有反向 WS。 |
| 钥匙串 / 密钥存储 | 仅保存 `secret_ref` 标识，没有真实密钥读写。 |
| 自动记忆抽取 / 向量检索 / MCP / 调度器 | 未实现。 |
| 登录 / 扫码 | 始终由 NapCat / SnowLuma 完成，Bellows 不接管 QQ 登录协议。 |

## 接入 NapCat / SnowLuma（反向 WS）

1. 在 NapCat 或 SnowLuma 中开启「反向 WebSocket」。
2. 连接地址填写：

   ```
   ws://127.0.0.1:7801/onebot/v11/ws/<实例ID>
   ```

   种子实例 `ins_second` 的 Access Token 为 `beta-token`；新建实例时填写的 Token 必须与协议端一致。留空则不校验。
3. 协议端连上后，实例状态变为「在线」，日志出现「协议端已连接实例 …」。
4. 群聊中 @ 机器人、消息含「风箱」或私聊消息会触发 BETA 规则回复；回复通过同一 WS 以 `send_msg` 动作发出。

调试用一次性入站消息（无需协议端）：

```bash
curl -s -X POST http://127.0.0.1:7801/api/debug/inbound \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"ins_main","text":"风箱，测试一条消息。","sender_name":"探针"}'
```

## 开发模式

```bash
# 终端 1：内核（自动重载可按需加 --reload 由 uvicorn 支持）
cd apps/core && python3 -m bellows_core --data-dir ../../data --port 7801

# 终端 2：前端（Vite 代理 /api 与 /onebot 到 7801）
cd apps/web && npm run dev
```

类型检查与构建：

```bash
cd apps/web && npm run type-check && npm run build
```

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查（唯一免鉴权 API） |
| GET | `/api/overview` | 总览聚合 |
| GET/POST | `/api/instances` | 实例列表 / 创建 |
| PATCH/DELETE | `/api/instances/{id}` | 更新 / 删除 |
| POST | `/api/instances/{id}/connect`、`/disconnect` | 连接 / 断开 |
| GET | `/api/instances/{id}/capabilities` | 能力探测 |
| GET | `/api/streams`、`/api/streams/{id}/messages` | 会话与消息 |
| POST | `/api/streams/{id}/send` | 人工发送（可选 AI 演示回复） |
| GET | `/api/events` | WebSocket 事件流 |
| WS | `/onebot/v11/ws/{instance_id}` | OneBot v11 反向 WS |
| CRUD | `/api/personas`、`/api/providers` | 人格 / Provider |
| GET/DELETE | `/api/memories` | 记忆 |
| GET | `/api/plugins`、`/api/plugins/market` | 插件 / 市场预览 |
| GET | `/api/logs`、`/api/audit` | 日志 / 审计 |
| GET/PUT | `/api/settings` | 设置 |

若启动时传入 `--token`，除 `/api/health` 外的 `/api` 请求需带 `Authorization: Bearer <token>`。

## 仓库结构

```
bellows/
├─ apps/
│  ├─ web/                 # Vue 3 + TS + Vite + Tailwind v4 + fuxsto-design
│  │  ├─ src/views/        # 总览 / 实例 / 控制台 / 人格 / 记忆 / 模型 / 插件 / 日志 / 设置
│  │  └─ dist/             # 构建产物（由 run.sh 生成）
│  └─ core/                # Python FastAPI 内核
│     └─ bellows_core/     # db / onebot / demo / events / api / app
├─ scripts/run.sh          # 单命令启动
├─ data/                   # 运行时 SQLite（首次启动自动创建）
├─ README.md
└─ LICENSE                 # AGPL-3.0
```

完整规划见仓库外的 `/workspace/PLAN.md`。

## 许可证

Copyright (C) 2026 Kei7295

本仓库以 [GNU Affero General Public License v3.0](LICENSE)（AGPL-3.0）发布。修改并通过网络提供服务时，须按 AGPL 第 13 条向用户提供对应源码。
