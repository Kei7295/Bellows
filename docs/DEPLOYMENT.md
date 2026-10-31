# 部署指南

Bellows 的目标场景是**个人本机**运行。以下方式同样适用于家庭服务器，但请先读 [SECURITY.md](../SECURITY.md)。

## 方式一：源码运行（推荐）

```bash
git clone https://github.com/Kei7295/Bellows.git
cd Bellows
bash scripts/run.sh
```

环境变量：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `BELLOWS_PORT` | `7801` | 监听端口 |
| `BELLOWS_DATA_DIR` | `./data` | SQLite 数据目录 |
| `BELLOWS_TOKEN` | 空 | 设置后除 `/api/health` 外均需 Bearer |
| `BELLOWS_LOG_LEVEL` | `info` | uvicorn 日志级别 |

参考 `.env.example`。

## 方式二：Docker

```bash
docker build -t bellows:0.0.1-beta .
docker run -d --name bellows \
  -p 127.0.0.1:7801:7801 \
  -e BELLOWS_TOKEN=change-me \
  -v "$PWD/data:/data" \
  bellows:0.0.1-beta
```

镜像内由同一进程托管 SPA 与 API；数据卷挂载到 `/data`。

### Docker Compose

```bash
cp .env.example .env   # 按需修改 Token
docker compose up -d --build
docker compose logs -f
```

`docker-compose.yml` 默认只绑定 `127.0.0.1:7801`，并把 `./data` 挂载为数据目录。

> 容器内 OneBot 协议端如需连接，请把协议端与本容器放在同一网络，并把反向 WS 地址指向容器服务名（如 `ws://bellows:7801/onebot/v11/ws/<实例ID>`）。QQ 协议端仍需自己完成登录，Bellows 不处理扫码。

## 方式三：systemd（Linux 服务器）

```ini
# /etc/systemd/system/bellows.service
[Unit]
Description=Bellows BOT workbench
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/Bellows/apps/core
Environment=BELLOWS_PORT=7801
Environment=BELLOWS_DATA_DIR=/opt/Bellows/data
Environment=BELLOWS_TOKEN=change-me
ExecStart=/usr/bin/python3 -m bellows_core
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bellows
```

## 反向代理

如确需跨机访问，至少做到：

1. 设置强随机 `BELLOWS_TOKEN`；
2. 仅监听内网 / 放在 TLS 反向代理后；
3. 限制来源 IP，不要把 `/api/debug/inbound` 暴露给不可信用户；
4. 不要转发 OneBot WS 给公网。

Nginx 示例（仅内网）：

```nginx
location / {
    proxy_pass http://127.0.0.1:7801;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

## 备份与恢复

- 备份：停止内核后复制整个 `data/`（含 `data.db`，建议连 `-wal`/`-shm` 一起）。
- 恢复：停进程 → 覆盖 `data/` → 启动。
- 升级：先备份 `data/`。BETA 的数据库结构与 API 可能变化，不保证向后兼容。

## 升级

```bash
git pull --ff-only
bash scripts/run.sh
```

前端改动后需重新 `npm run build`（`run.sh` 只在 dist 缺失时构建）。
