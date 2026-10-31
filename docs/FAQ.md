# 常见问题（FAQ）

## 这是完整的 QQ 机器人吗？

不是。Bellows 是**本地工作台**：管理实例、查看消息、配置人格/Provider/插件。QQ 登录与协议由 NapCat / SnowLuma 完成，Bellows 通过 OneBot v11 反向 WS 接入。

## 为什么回复像是固定的？

v0.0.1 BETA **没有接入真实 LLM**。`reply.py` 是规则引擎，Provider 的「测试」也是模拟探测。真实推理在后续版本。

## 有桌面安装包吗？

有 Windows 版。GitHub Actions 在 `windows-latest` 上把 Web 前端与 Python 内核打进单文件 sidecar，再由 Tauri 2 封装成 NSIS 安装包，可从 [Releases](https://github.com/Kei7295/Bellows/releases/latest) 或 Actions 的 `bellows-windows-nsis` 产物下载。

安装包未做代码签名，SmartScreen 可能提示「未知发布者」。桌面版会自己启动内置内核，数据写入 `%APPDATA%\dev.bellows.desktop`，不需要本机安装 Python 或 Node。其他平台仍用 `bash scripts/run.sh` 或 Docker。

## 端口/数据放哪？

- 默认 `http://127.0.0.1:7801`，`BELLOWS_PORT` 可改。
- 数据在 `data/data.db`（SQLite WAL），`BELLOWS_DATA_DIR` 可改。
- 重置：停止后删除 `data/`，重启会重建种子数据。

## 需要设置 Token 吗？

仅本机使用可以不设。只要可能被其他机器访问，就必须设置 `BELLOWS_TOKEN`，并最好放在反向代理后。`/api/health` 始终免鉴权。

## 协议端连不上 / 一直离线？

1. 确认协议端使用的是「反向 WebSocket」，而不是正向。
2. 地址必须是 `ws://127.0.0.1:7801/onebot/v11/ws/<实例ID>`，实例 ID 在实例页可查。
3. 实例配置了 Token 时，协议端也必须配置同一 Token，否则会被 1008 关闭。
4. 看「日志」页是否出现鉴权失败或连接断开记录。

## 演示消息怎么关？

演示管线由内核内置，BETA 未提供 UI 开关。它会持续产生示例消息，便于无协议端时验证界面；接入真实协议端后同样会运行。后续版本会提供开关。

## 能装插件吗？

不能。插件市场是只读预览，开关只写数据库与审计日志，运行时不加载，`reload` 返回未实现。

## 升级会丢数据吗？

BETA 期间数据库结构可能变化，升级前请备份 `data/`。没有自动迁移承诺。

## macOS / Windows 能用吗？

可以，需要 Python ≥ 3.12 与 Node.js（构建前端）。WSL 也可。Docker 方式见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 为什么采用 AGPL-3.0？

希望修改后的网络服务版本也回馈源码。若你需要更宽松的许可用于商业闭源，请先联系维护者讨论。

## 发现安全漏洞怎么办？

不要公开开 Issue，按 [SECURITY.md](../SECURITY.md) 私下报告。
