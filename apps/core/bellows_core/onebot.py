"""OneBot v11 adapter: reverse server + forward client (BETA).

Two connection directions share one event pipeline:

* ``reverse_ws`` — NapCat / SnowLuma connect to
  ``/onebot/v11/ws/<instance_id>``; actions go back on the same socket.
* ``forward_ws`` — Bellows connects outward to ORBIT's
  ``/onebot/ws?access_token=...`` (MaiBot-style), subscribes to events and
  sends actions either over the socket or through ORBIT's HTTP endpoint.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from typing import Any

import websockets
from fastapi import WebSocket

from .db import Database, new_id, now_iso
from .events import EventBus
from .orbit import OrbitError, endpoints, http_action
from .reply import generate

MAX_TEXT = 5000
FORWARD_RECV_TIMEOUT = 40.0
FORWARD_BACKOFF_MAX = 30.0


class ForwardLink:
    """Runtime state for one outbound ORBIT connection."""

    def __init__(self) -> None:
        self.task: asyncio.Task[None] | None = None
        self.ws: Any = None
        self.stop = asyncio.Event()
        self.attempts = 0
        self.probes: dict[str, float] = {}


class OneBotManager:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus
        self.sockets: dict[str, WebSocket] = {}
        self.forward: dict[str, ForwardLink] = {}
        self.lost: dict[str, float] = {}

    async def accept(self, instance_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.sockets[instance_id] = ws
        self.db.execute(
            "UPDATE instances SET status='online', latency_ms=18, updated_at=? WHERE id=?",
            (now_iso(), instance_id),
        )
        await ws.send_text(
            json.dumps(
                {
                    "action": "get_login_info",
                    "params": {},
                    "echo": f"hello_{uuid.uuid4().hex[:6]}",
                },
                ensure_ascii=False,
            )
        )
        self.bus.publish(
            "instance.status", {"id": instance_id, "status": "online", "latency_ms": 18}
        )
        self.db.log(
            "info",
            "onebot",
            f"协议端已连接实例 {instance_id}",
            {"instance": instance_id},
        )
        self.bus.publish(
            "log.appended",
            {
                "level": "info",
                "source": "onebot",
                "message": f"协议端已连接实例 {instance_id}",
            },
        )

    def drop(self, instance_id: str) -> None:
        self.sockets.pop(instance_id, None)
        self.lost[instance_id] = time.time()

    async def disconnect(self, instance_id: str) -> None:
        ws = self.sockets.pop(instance_id, None)
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass
        await self.stop_forward(instance_id)

    # -- forward websocket (Bellows -> ORBIT) ----------------------------
    def _set_status(self, instance_id: str, status: str, latency_ms: int | None = None) -> None:
        if latency_ms is None:
            self.db.execute(
                "UPDATE instances SET status=?, latency_ms=NULL, updated_at=? WHERE id=?",
                (status, now_iso(), instance_id),
            )
        else:
            self.db.execute(
                "UPDATE instances SET status=?, latency_ms=?, updated_at=? WHERE id=?",
                (status, latency_ms, now_iso(), instance_id),
            )
        payload: dict[str, Any] = {"id": instance_id, "status": status}
        if latency_ms is not None:
            payload["latency_ms"] = latency_ms
        self.bus.publish("instance.status", payload)

    def _log(self, level: str, message: str, instance_id: str) -> None:
        self.bus.publish(
            "log.appended",
            self.db.log(level, "onebot", message, {"instance": instance_id}),
        )

    async def start_forward(self, instance_id: str) -> dict[str, Any]:
        """Start (or restart) the outbound ORBIT connection for an instance."""
        inst = self.db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
        if not inst:
            return {"ok": False, "status": "error", "message": "实例不存在"}
        if inst["mode"] != "forward_ws":
            return {"ok": False, "status": "error", "message": "实例不是正向 WS 模式"}
        try:
            urls = endpoints(inst["endpoint"], inst["access_token"])
        except OrbitError as exc:
            self._set_status(instance_id, "error")
            self._log("error", f"实例 {instance_id} 无法连接 ORBIT：{exc}", instance_id)
            return {"ok": False, "status": "error", "message": str(exc)}

        await self.stop_forward(instance_id)
        link = ForwardLink()
        self.forward[instance_id] = link
        self._set_status(instance_id, "connecting")
        link.task = asyncio.create_task(self._forward_loop(instance_id, link))
        self._log("info", f"正在连接 ORBIT：{urls['ws_url']}", instance_id)
        return {
            "ok": True,
            "status": "connecting",
            "message": f"正在连接 ORBIT：{urls['ws_url']}",
        }

    async def stop_forward(self, instance_id: str) -> None:
        link = self.forward.pop(instance_id, None)
        if link is None:
            return
        link.stop.set()
        if link.task is not None:
            link.task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await link.task
        ws, link.ws = link.ws, None
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close()

    async def resume_forward(self) -> None:
        """Reconnect opted-in forward instances after a core restart."""
        rows = self.db.query(
            "SELECT id, endpoint, config_json FROM instances WHERE mode='forward_ws'"
        )
        for row in rows:
            try:
                config = json.loads(row["config_json"] or "{}")
            except json.JSONDecodeError:
                config = {}
            if config.get("auto_reconnect", True) and row["endpoint"]:
                await self.start_forward(row["id"])

    async def shutdown(self) -> None:
        for instance_id in list(self.forward):
            await self.stop_forward(instance_id)

    async def _forward_loop(self, instance_id: str, link: ForwardLink) -> None:
        delay = 1.0
        while not link.stop.is_set():
            inst = self.db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
            if not inst or inst["mode"] != "forward_ws":
                break
            try:
                urls = endpoints(inst["endpoint"], inst["access_token"])
            except OrbitError as exc:
                self._set_status(instance_id, "error")
                self._log("error", f"实例 {instance_id} 地址无效：{exc}", instance_id)
                break

            try:
                async with websockets.connect(
                    urls["ws_url"],
                    open_timeout=6,
                    ping_interval=None,
                    close_timeout=3,
                    max_size=4 * 1024 * 1024,
                ) as ws:
                    link.ws = ws
                    link.attempts = 0
                    delay = 1.0
                    self._set_status(instance_id, "online")
                    self._log("info", f"实例 {instance_id} 已连接 ORBIT 正向 WS", instance_id)
                    probe_echo = f"probe_{uuid.uuid4().hex[:8]}"
                    link.probes[probe_echo] = time.perf_counter()
                    await ws.send(
                        json.dumps(
                            {"action": "get_status", "params": {}, "echo": probe_echo},
                            ensure_ascii=False,
                        )
                    )
                    while not link.stop.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=FORWARD_RECV_TIMEOUT)
                        payload = json.loads(raw)
                        if not isinstance(payload, dict):
                            continue
                        if payload.get("post_type"):
                            await self.handle_event(instance_id, payload)
                        else:
                            self._handle_action_response(instance_id, link, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if link.stop.is_set():
                    break
                link.attempts += 1
                self._set_status(instance_id, "offline")
                self._log(
                    "warn",
                    f"实例 {instance_id} 与 ORBIT 的连接中断（第 {link.attempts} 次）：{exc}",
                    instance_id,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, FORWARD_BACKOFF_MAX)
                if not link.stop.is_set():
                    self._set_status(instance_id, "connecting")
            finally:
                link.ws = None

        if not link.stop.is_set():
            self._set_status(instance_id, "offline")

    def _handle_action_response(
        self, instance_id: str, link: ForwardLink, payload: dict[str, Any]
    ) -> None:
        echo = payload.get("echo")
        if not isinstance(echo, str):
            return
        started = link.probes.pop(echo, None)
        if started is None:
            return
        latency = max(1, int((time.perf_counter() - started) * 1000))
        self._set_status(instance_id, "online", latency)
        self._log("info", f"实例 {instance_id} ORBIT 往返延迟 {latency} ms", instance_id)

    async def send_action(self, instance_id: str, action: str, params: dict[str, Any]) -> bool:
        ws = self.sockets.get(instance_id)
        if ws is not None:
            try:
                await ws.send_text(
                    json.dumps(
                        {
                            "action": action,
                            "params": params,
                            "echo": f"act_{uuid.uuid4().hex[:8]}",
                        },
                        ensure_ascii=False,
                    )
                )
                return True
            except Exception:
                self.sockets.pop(instance_id, None)

        link = self.forward.get(instance_id)
        if link is not None and link.ws is not None:
            try:
                await link.ws.send(
                    json.dumps(
                        {
                            "action": action,
                            "params": params,
                            "echo": f"act_{uuid.uuid4().hex[:8]}",
                        },
                        ensure_ascii=False,
                    )
                )
                return True
            except Exception:
                link.ws = None

        inst = self.db.one(
            "SELECT mode, endpoint, access_token FROM instances WHERE id=?",
            (instance_id,),
        )
        if inst and inst["mode"] == "forward_ws":
            return await http_action(inst["endpoint"], inst["access_token"], action, params)
        return False

    async def handle_event(self, instance_id: str, raw: dict[str, Any]) -> None:
        """Normalize an incoming OneBot event into a stored ChatEvent."""
        post_type = raw.get("post_type")
        if post_type == "meta_event":
            self_id = str(raw.get("self_id", "") or "")
            if self_id and self_id != "0":
                self.db.execute(
                    "UPDATE instances SET self_id=?, updated_at=? WHERE id=?",
                    (self_id, now_iso(), instance_id),
                )
                self.db.execute(
                    "INSERT INTO settings (key,value_json) VALUES (?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                    (
                        f"account:{instance_id}",
                        json.dumps({"uin": self_id}, ensure_ascii=False),
                    ),
                )
            else:
                self.db.execute(
                    "UPDATE instances SET updated_at=? WHERE id=?",
                    (now_iso(), instance_id),
                )
            return
        if post_type != "message":
            return

        scene = "group" if raw.get("message_type") == "group" else "private"
        sender = raw.get("sender") or {}
        sender_id = str(raw.get("user_id", ""))
        sender_name = sender.get("card") or sender.get("nickname") or sender_id
        self_id = str(raw.get("self_id", ""))
        group_id = str(raw.get("group_id", "")) if scene == "group" else None
        peer_id = group_id or sender_id
        raw_message = raw.get("message")
        if isinstance(raw_message, str):
            segments = [{"type": "text", "text": raw_message[:MAX_TEXT]}]
        elif isinstance(raw_message, list):
            segments = raw_message
        else:
            segments = []
        text = _segments_to_text(segments) or str(raw.get("raw_message", ""))[:MAX_TEXT]

        stream = self.db.one(
            "SELECT id FROM streams WHERE instance_id=? AND peer_id=? AND scene=?",
            (instance_id, peer_id, scene),
        )
        if stream:
            stream_id = stream["id"]
            self.db.execute(
                "UPDATE streams SET last_message_at=?, unread=unread+1 WHERE id=?",
                (now_iso(), stream_id),
            )
        else:
            stream_id = new_id("st")
            title = sender_name if scene == "private" else f"群 {peer_id}"
            self.db.insert(
                "streams",
                {
                    "id": stream_id,
                    "instance_id": instance_id,
                    "scene": scene,
                    "peer_id": peer_id,
                    "group_id": group_id,
                    "title": title,
                    "subtitle": "来自协议端的新会话",
                    "last_message_at": now_iso(),
                    "unread": 1,
                },
            )

        message = store_message(
            self.db,
            stream_id,
            instance_id,
            raw.get("message_id"),
            "in",
            sender_id,
            sender_name,
            segments,
            text,
            False,
            raw,
        )
        self.bus.publish("message.created", message)
        self.db.execute(
            "INSERT INTO stats_daily (date, messages, replies, tokens) VALUES (date('now'), 1, 0, 0) "
            "ON CONFLICT(date) DO UPDATE SET messages=messages+1"
        )

        mentioned = _mentions_self(segments, self_id)
        if scene == "private" or mentioned or "风箱" in text:
            await asyncio.sleep(0.4)
            reply = generate(text)
            out_message = store_message(
                self.db,
                stream_id,
                instance_id,
                None,
                "out",
                self_id,
                "风箱",
                [{"type": "text", "text": reply}],
                reply,
                True,
                None,
            )
            self.bus.publish("message.created", out_message)
            self.db.execute("UPDATE stats_daily SET replies=replies+1 WHERE date=date('now')")
            self.db.execute(
                "UPDATE streams SET last_message_at=? WHERE id=?",
                (now_iso(), stream_id),
            )
            await self.send_action(
                instance_id,
                "send_msg",
                {
                    "message_type": scene,
                    "user_id": int(sender_id) if sender_id.isdigit() else sender_id,
                    "group_id": int(peer_id) if scene == "group" and peer_id.isdigit() else None,
                    "message": [{"type": "text", "data": {"text": reply}}],
                },
            )


def _segments_to_text(segments: Any) -> str:
    if not isinstance(segments, list):
        return ""
    parts = []
    for seg in segments:
        if isinstance(seg, str):
            parts.append(seg)
            continue
        data = seg.get("data") or {}
        typ = seg.get("type")
        if typ == "text":
            parts.append(str(data.get("text", "")))
        elif typ == "at":
            parts.append(f"@{data.get('qq', '')}")
    return "".join(parts).strip()


def _mentions_self(segments: Any, self_id: str) -> bool:
    if not isinstance(segments, list):
        return False
    return any(
        seg.get("type") == "at" and str((seg.get("data") or {}).get("qq")) == self_id
        for seg in segments
    )


def store_message(
    db: Database,
    stream_id: str,
    instance_id: str,
    message_id: Any,
    direction: str,
    sender_id: str,
    sender_name: str,
    segments: list,
    text: str,
    is_bot: bool,
    raw: dict | None,
) -> dict[str, Any]:
    row = {
        "id": new_id("msg"),
        "stream_id": stream_id,
        "instance_id": instance_id,
        "message_id": str(message_id) if message_id is not None else None,
        "direction": direction,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "segments_json": json.dumps(segments, ensure_ascii=False),
        "text": text,
        "is_bot": 1 if is_bot else 0,
        "raw_json": json.dumps(raw, ensure_ascii=False) if raw else None,
        "created_at": now_iso(),
    }
    db.insert("messages", row)
    return {k: v for k, v in row.items() if k != "raw_json"} | {"segments": segments}
