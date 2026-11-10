# OneBot v11 接入（反向 WS / ORBIT 正向 WS）

v0.0.1 BETA 支持两种方向：

- **反向 WS**：Bellows 作为服务端，NapCat / SnowLuma 主动连入。
- **正向 WS**：Bellows 作为 OneBot 客户端，主动外连 [ORBIT（星轨）](https://github.com/Kei7295/XingGui-ORBIT)，方向与 MaiBot 相同。

QQ 登录、扫码、风控始终由协议端负责。

## 连接地址

```
ws://127.0.0.1:7801/onebot/v11/ws/<instance_id>
```

- `instance_id` 可在「实例」页查看；种子实例为 `ins_main`、`ins_second`、`ins_demo`。
- 实例状态会在协议端连入后变为 `online`；断开后变回 `offline`，并写入日志。

## Token

- 创建/编辑实例时可填 `access_token`；协议端需在请求头带上 `Authorization: Bearer <token>`。
- 实例 Token 留空表示该端点不校验，仅建议在本机使用。
- 种子实例 `ins_second` 的 Token 为 `beta-token`。

## 在 NapCat 中配置

1. 打开 NapCat 配置，启用「反向 WebSocket」。
2. 地址填 `ws://127.0.0.1:7801/onebot/v11/ws/ins_main`。
3. 如实例配置了 Token，把同一 Token 填到协议端的 Access Token。
4. 保存并重连；Bellows 实例页应显示在线。

SnowLuma 同理，入口名称可能是「反向 WS / WebSocket 服务端」。

## 正向 WebSocket（ORBIT / 星轨）

ORBIT 提供 OneBot 11 的 HTTP 与正向 WS 接口。风箱「实例」页右上角的「接入 ORBIT」会完成探测、建实例与连接，也可以手动调用 API（见 [API.md](API.md#orbit星轨正向-ws)）。

1. 启动 ORBIT（Node ≥ 20）：`npm install && npm run build && npm start`，默认 `http://127.0.0.1:8787`。
2. 在风箱填写 ORBIT 地址与 Access Token（默认 `orbit-demo-token`），点「探测」。
3. 点「接入并连接」后，实例以 `forward_ws` 模式保存：
   - `endpoint` = `ws://127.0.0.1:8787/onebot/ws`（连接时再拼 `access_token` 查询参数）
   - `access_token` = ORBIT Access Token
   - `config.protocol` = `ORBIT`
4. 连上后 ORBIT 先下发 `meta_event/lifecycle` 与 30s 心跳，风箱据此更新 `self_id` 与在线状态；消息事件进入与反向 WS 相同的归一化管线。
5. 外连断开按 1s → 30s 指数退避重连；WS 不可用时回复动作自动回退到 `POST /onebot`。

## 事件处理

服务端接收 OneBot v11 事件（需含 `post_type`），当前支持的归一化范围：

- `message`（私聊 `private` / 群聊 `group`）：提取 `message` 段（text、image、at 等）与纯文本；兼容 ORBIT 直接下发字符串 `message` 的写法。
- 发送者信息 `user_id`、`nickname`、群号等写入会话与消息记录。
- 事件同时写入 `stats_daily` 与日志，并通过 `/api/events` 推送到前端。

未识别的事件会被忽略，不会导致连接断开。

## 回复行为

BETA 由 `reply.py` 的规则引擎生成回复，触发条件包括：

- 群聊中被 @；
- 消息文本包含「风箱」；
- 私聊消息。

回复通过同一 WebSocket 下发：

```json
{
  "action": "send_msg",
  "params": {
    "message_type": "group",
    "group_id": "123456",
    "user_id": "123456",
    "message": [{"type": "text", "data": {"text": "..."}}]
  }
}
```

这不是 LLM 输出，接入真实模型属于后续版本。

## 调试

没有协议端时，用调试接口注入消息：

```bash
curl -s -X POST http://127.0.0.1:7801/api/debug/inbound \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"ins_main","text":"风箱，测试一条消息。","sender_name":"探针"}'
```

也可以在「控制台」页直接人工发送，观察落库、事件流与在线实例下发。

## 排查

| 现象 | 检查 |
| --- | --- |
| 实例一直 offline | 协议端是否真的连上？地址中的实例 ID 是否正确？ |
| 连上立刻断开（1008） | Token 与实例配置不一致，或实例 ID 不存在 |
| 收不到回复 | 实例是否 online？是否命中触发条件？规则引擎不处理所有消息 |
| 乱码 / 分段异常 | 查看 `/api/streams/{id}/messages/raw/{message_id}` 的原始事件 |
| 多实例混淆 | 每个协议端连接必须使用各自的实例 ID 与 Token |
| ORBIT 探测失败 | ORBIT 是否已启动？地址端口是否为 8787？Token 是否与 `ORBIT_ACCESS_TOKEN` 一致？ |
| ORBIT 显示 connecting / offline | 看日志中的中断原因；风箱会自动重试，也可手动点「连接」 |
