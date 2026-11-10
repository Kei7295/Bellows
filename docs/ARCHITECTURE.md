# 架构说明

Bellows v0.0.1 BETA 是一个**单进程、本机运行**的工作台：Python 内核同时提供 REST API、两个 WebSocket 端点，并托管编译后的 Vue SPA。

```text
┌─────────────────────────────────────────────────────────────┐
│                        浏览器 SPA                           │
│  Vue 3 + Pinia + Vue Router + Tailwind v4 + fuxsto-design   │
│  /api/*  ───────────────┐            /api/events (WS) ───┐  │
└─────────────────────────┼───────────────────────────────┼──┘
                          │                               │
┌─────────────────────────▼───────────────────────────────▼──┐
│                   FastAPI 内核（apps/core）                 │
│                                                            │
│  api_instances / api_content / api_orbit → Runtime(...)     │
│  OneBotManager（反向 WS 服务端 + ORBIT 正向 WS 客户端）     │
│  DemoEngine（每 11–18s 演示事件）                           │
│  EventBus（内存 pub/sub → /api/events）                     │
│  Database（SQLite WAL，data/data.db）                       │
└──────────┬─────────────────────────────┬───────────────────┘
           │ 反向 WS                     │ 正向 WS 外连
┌──────────▼───────────────┐  ┌──────────▼───────────────────┐
│ NapCat / SnowLuma        │  │ ORBIT 星轨（OneBot 11 协议端）│
│ （自行登录 QQ）           │  │ HTTP 动作回退 /onebot         │
└──────────────────────────┘  └──────────────────────────────┘
```

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `app.py` | 创建 FastAPI 实例、鉴权中间件、`/api/health`、`/api/overview`、`/api/events`、OneBot WS 入口、SPA 静态托管 |
| `api_instances.py` | 实例 CRUD、连接/断开、能力探测、会话与消息、人工发送 |
| `api_content.py` | 人格、Provider、记忆、插件、日志、审计、设置 |
| `api_orbit.py` | ORBIT 探测与一键接入，创建/复用 `forward_ws` 实例 |
| `orbit.py` | ORBIT 地址归一化、HTTP 动作、`get_login_info` 探测 |
| `onebot.py` | OneBot v11 事件解析、消息落库、`send_msg` 动作、反向/正向连接管理 |
| `reply.py` | BETA 规则回复引擎（非 LLM） |
| `demo.py` | 演示管线：定时生成入站消息与规则回复 |
| `events.py` | 进程内事件总线，供 `/api/events` 推送 |
| `db.py` | SQLite 连接、建表、种子数据、日志写入 |
| `runtime.py` | 单例运行时容器（db / bus / data_dir / token / uptime） |
| `__main__.py` | CLI、端口协商、启动握手行、uvicorn 启动 |

## 数据流

### 入站消息

1. 协议端通过反向 WS 发送 OneBot v11 事件（`post_type: message`）。
2. `OneBotManager.handle_event` 归一化为 `segments` + 纯文本，写入 `messages` 与 `stats_daily`。
3. `EventBus` 发布 `message.created` 与 `log.appended`，`/api/events` 立即推给前端。
4. 命中规则时 `reply.py` 生成回复，经同一 WS 以 `send_msg` 发出，并再次落库。

### ORBIT 正向 WS

1. `POST /api/orbit/connect`（或实例页向导）先通过 HTTP 调 `get_login_info` 探测账号，再创建/复用 `forward_ws` 实例并启动外连。
2. `OneBotManager._forward_loop` 连接 `ws://<orbit>/onebot/ws?access_token=...`，订阅 `meta_event` 与 `message`，并记录往返延迟。
3. 事件复用 `handle_event` 的归一化、落库、广播与规则回复路径；回复优先走当前 WS，断线时回退到 ORBIT 的 `POST /onebot`。
4. 断线按 1s→30s 指数退避重连；内核启动时自动恢复 `auto_reconnect` 为 true 的实例。

### 人工发送

`POST /api/streams/{id}/send` → 落库 → 广播 → 若实例在线则调用 `send_msg`；`use_ai: true` 时延迟 1.4s 追加一条规则回复（模拟流水，不代表真实推理）。

### 演示管线

`DemoEngine` 仅在 BETA 中按 11–18 秒随机间隔产生入站消息，走与真实事件相同的落库与广播路径，因此不接协议端也能验证 UI/API。

## 数据库

单文件 SQLite（WAL）。表：`instances`、`streams`、`messages`、`personas`、`providers`、`memories`、`plugins`、`logs`、`stats_daily`、`settings`。首次启动写入种子数据（3 实例、6 会话、30 消息、14 天统计等）。删除 `data/` 即重置。

## 鉴权

- 启动传入 `--token` / `BELLOWS_TOKEN` 后，除 `/api/health` 外的 `/api` 与 `/api/events` 需要 `Authorization: Bearer <token>` 或 `?token=`。
- OneBot 反向 WS 使用实例级 `access_token`；实例未配置 Token 时不校验。
- ORBIT 正向 WS 使用 ORBIT 自己的 `access_token`（默认 `orbit-demo-token`），通过查询参数与 Bearer 头传递。
- 没有用户体系与 RBAC，BETA 只面向本机可信环境。

## 前端组织

- `App.vue` 桌面式壳：自定义标题栏 + 可折叠侧栏。
- `views/*` 九个页面；`api.ts` 统一封装 REST 与事件流；`stores/app.ts` 保存主题与全局状态。
- 构建产物 `apps/web/dist` 由内核 `/` 托管，未命中路径回退到 `index.html`。

## 桌面壳（Windows）

`apps/desktop` 是 Tauri 2 外壳，`apps/desktop/src-tauri/src/main.rs` 负责：

1. 先绑定 `127.0.0.1` 的空闲端口并**立即显示本地启动页**（`apps/desktop/ui/index.html`），用户不会对着空白桌面等；
2. 启动 PyInstaller 打包的 `bellows-core`（`--onedir`，免去每次启动的解包开销），数据目录指向 Tauri 的 `app_data_dir`；
3. 通过 `boot-progress` 事件把启动阶段推给启动页（进度条 + 文案）；
4. 短间隔轮询 `/api/health`，就绪后把同一个窗口导航到 `http://127.0.0.1:<port>` 并放大到工作台尺寸；
5. 应用退出时杀掉 sidecar，避免残留 Python 进程。

内核照常打印握手行，桌面壳也可以选择解析它而不是健康检查：

```text
BELLOWS-CORE {"port": 7801, "token": "", "pid": 1234, "version": "0.0.1-beta", "data_dir": "..."}
```

`packaging/build_sidecar.py` 用 PyInstaller `--onedir` 把内核与 `apps/web/dist` 打进 `apps/desktop/src-tauri/sidecar/`，再由 Tauri 作为 resource 一起安装；内核通过 `BELLOWS_WEB_DIST` 找到包内的前端资源。当前只发布 Windows（NSIS），macOS / Linux 桌面包未验证。
