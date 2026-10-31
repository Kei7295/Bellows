# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.0.1-beta] - 2026-10-31

首个公开测试版本，仅覆盖「本机工作台 + OneBot v11 反向 WS + 演示管线」。

### 新增

- 单命令启动：`bash scripts/run.sh`，自动构建前端并启动 Python 内核（默认 `127.0.0.1:7801`）。
- 桌面式 App Shell：自定义标题栏、可折叠侧栏、亮/暗/跟随系统主题。
- 总览页：在线实例、今日消息/回复/Token、14 天趋势、事件流、告警。
- 实例管理：CRUD、连接/断开、能力探测、原始配置查看。
- OneBot v11 反向 WebSocket：`ws://127.0.0.1:7801/onebot/v11/ws/{instance_id}`，支持 Bearer Token 校验。
- 消息归一化与落库、`/api/events` 实时推送、消息控制台人工发送。
- 演示管线：每 11–18 秒生成入站消息与规则回复，无需真实 QQ 账号。
- 内容管理：会话列表与检索、人格 CRUD、Provider CRUD、记忆浏览/删除。
- 插件列表与开关、只读插件市场预览（运行时不加载）。
- 日志/审计检索、设置持久化。
- SQLite 持久化与首次种子数据（3 实例、6 会话、30 消息、14 天统计等）。
- AGPL-3.0 开源许可证。
- 应用图标：Pillow 可复现生成 ICO/PNG，Web 端接入 favicon。
- Windows 桌面版：Tauri 2 壳 + PyInstaller sidecar + NSIS 安装包，GitHub Actions 构建并归档。

### 已知限制

- 桌面版仅 Windows；安装包未签名，SmartScreen 会提示「未知发布者」；暂无自动更新。
- 未接入真实 LLM；Provider 测试为模拟探测，回复由规则引擎生成。
- 插件运行时未实现，开关仅更新数据库与审计日志。
- 仅支持反向 WS，正向 WS / HTTP 接入为 scaffold。
- 未实现钥匙串、自动记忆抽取、向量检索、MCP 与调度器。
- 登录/扫码由 NapCat / SnowLuma 完成，Bellows 不接管 QQ 登录协议。

### 变更

- 路由与 API 在 BETA 期间可能不兼容地调整，升级前请备份 `data/`。
