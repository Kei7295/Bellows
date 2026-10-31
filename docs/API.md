# API 参考（v0.0.1 BETA）

Base URL：`http://127.0.0.1:7801`。BETA 期间路径与字段可能调整。

## 鉴权

- 启动时设置 `--token` / `BELLOWS_TOKEN` 后，除 `/api/health` 外的 `/api` 请求需要 `Authorization: Bearer <token>`，也可用查询参数 `?token=`。
- WebSocket `/api/events` 同样校验 Token。
- 错误响应统一为 `{"code": "...", "message": "..."}`。

## 健康与元信息

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 唯一免鉴权接口，返回 `status/version/build/uptime/data_dir/beta` |
| GET | `/api/meta` | 应用标识、版本、标语 |
| GET | `/api/overview` | 总览聚合：`stats`、`series`（14 天）、`instances`、`recent`、`alerts` |
| GET | `/api/events` | 事件流说明（`transport: websocket`） |
| WS | `/api/events` | 实时事件，消息形如 `{type, ts, data}`；25s 空闲发送 `ping` |

事件类型：`core.ready`、`message.created`、`instance.status`、`log.appended`；`ping` 为心跳。

## 实例

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/instances` | 列表，附带 `account` 设置 |
| POST | `/api/instances` | 创建；字段 `name`（必填）、`mode`、`endpoint`、`access_token`、`self_id`、`platform`、`protocol` |
| PATCH | `/api/instances/{id}` | 局部更新；不存在返回 404 |
| DELETE | `/api/instances/{id}` | 同时删除该实例的会话与消息 |
| POST | `/api/instances/{id}/connect` | `demo` 置在线；`reverse_ws` 置 connecting；其他模式返回 error |
| POST | `/api/instances/{id}/disconnect` | 断开 WS 并置 offline |
| GET | `/api/instances/{id}/capabilities` | 返回能力探测结果（发送/撤回/群列表等） |

## 会话与消息

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/streams` | 查询参数 `instance_id`、`scene`、`q`；附 `last_text`/`last_sender` |
| GET | `/api/streams/{id}` | 会话详情 + `message_count` + 当前人格 |
| GET | `/api/streams/{id}/messages` | `limit`（1–300，默认 80）、`before`（时间游标），按时间正序返回 |
| GET | `/api/streams/{id}/messages/raw/{message_id}` | 归一化消息 + 原始 OneBot JSON |
| POST | `/api/streams/{id}/send` | 人工发送；`{"text": "...", "use_ai": false}`，空文本返回 400 |

消息对象字段：`id`、`stream_id`、`instance_id`、`message_id`、`direction`（in/out）、`sender_id`、`sender_name`、`segments`、`text`、`is_bot`、`created_at`。

## OneBot v11 反向 WebSocket

```
ws://127.0.0.1:7801/onebot/v11/ws/{instance_id}
```

- 实例不存在 → 关闭码 1008。
- 实例配置了 `access_token` 时，需带 `Authorization: Bearer <token>`，否则 1008。
- 接收 OneBot v11 事件 JSON（需含 `post_type`）；服务端可主动下发 `send_msg` 动作。

## 人格

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/personas` | 列表（`style` 已解码、`enabled` 已布尔化） |
| POST | `/api/personas` | `name`、`description`、`prompt`、`scope`、`enabled`、`style` |
| PATCH | `/api/personas/{id}` | 接受任意上述字段的子集 |
| DELETE | `/api/personas/{id}` | 删除 |

## Provider（模型服务商）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/providers` | 列表；`has_key` 表示是否配置 `secret_ref` |
| POST | `/api/providers` | `name`、`type`、`base_url`、`model`、`enabled`、`params` |
| PATCH | `/api/providers/{id}` | 局部更新 |
| DELETE | `/api/providers/{id}` | 删除 |
| POST | `/api/providers/{id}/test` | **模拟**探测，返回 `mode: "simulated"`，不发真实请求 |

## 记忆

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/memories` | 支持 `scope`、`q` 等查询（以实际实现为准） |
| DELETE | `/api/memories/{id}` | 删除单条记忆 |

BETA 没有自动抽取与向量检索，记忆只做展示与管理。

## 插件

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/plugins` | 列表与状态 |
| POST | `/api/plugins/{id}/toggle` | `{"enabled": true}`；仅更新库与审计 |
| POST | `/api/plugins/{id}/reload` | BETA 返回未实现 |
| GET | `/api/plugins/market` | 只读市场预览，不能安装 |

## 日志、审计与设置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/logs` | 支持 `level`、`source`、`limit` 等过滤 |
| GET | `/api/audit` | 审计记录 |
| GET | `/api/settings` | 设置对象 |
| PUT | `/api/settings` | 整体保存设置 |

## 调试

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/debug/inbound` | 注入一条入站消息，无需协议端；字段 `instance_id`、`stream_id`、`text`、`sender_id`、`sender_name`；无可用会话返回 404 |

```bash
curl -s -X POST http://127.0.0.1:7801/api/debug/inbound \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"ins_main","text":"风箱，测试一条消息。","sender_name":"探针"}'
```

## 常见状态码

| 码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 请求内容无效（如空消息） |
| 401 | Token 缺失或不匹配 |
| 404 | 实例/会话/消息不存在 |
| 1008 | WebSocket 鉴权失败或实例不存在 |
