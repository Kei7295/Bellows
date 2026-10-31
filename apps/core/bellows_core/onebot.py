"""OneBot v11 reverse WebSocket adapter (BETA).

NapCat / SnowLuma connect to /onebot/v11/ws/<instance_id>. Events are normalized,
stored and broadcast. Actions are written back on the same socket. Outbound
HTTP/forward-WS modes are scaffolded but not active in v0.0.1.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import WebSocket

from .db import Database, new_id, now_iso
from .events import EventBus
from .reply import generate

MAX_TEXT = 5000


class OneBotManager:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus
        self.sockets: dict[str, WebSocket] = {}
        self.lost: dict[str, float] = {}

    async def accept(self, instance_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.sockets[instance_id] = ws
        self.db.execute(
            "UPDATE instances SET status='online', latency_ms=18, updated_at=? WHERE id=?",
            (now_iso(), instance_id),
        )
        await ws.send_text(json.dumps({
            "action": "get_login_info", "params": {}, "echo": f"hello_{uuid.uuid4().hex[:6]}",
        }, ensure_ascii=False))
        self.bus.publish("instance.status", {"id": instance_id, "status": "online", "latency_ms": 18})
        self.db.log("info", "onebot", f"协议端已连接实例 {instance_id}", {"instance": instance_id})
        self.bus.publish("log.appended", {"level": "info", "source": "onebot", "message": f"协议端已连接实例 {instance_id}"})

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

    async def send_action(self, instance_id: str, action: str, params: dict[str, Any]) -> bool:
        ws = self.sockets.get(instance_id)
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps({"action": action, "params": params,
                                           "echo": f"act_{uuid.uuid4().hex[:8]}"}, ensure_ascii=False))
            return True
        except Exception:
            self.sockets.pop(instance_id, None)
            return False

    async def handle_event(self, instance_id: str, raw: dict[str, Any]) -> None:
        """Normalize an incoming OneBot event into a stored ChatEvent."""
        post_type = raw.get("post_type")
        if post_type == "meta_event":
            self_id = str(raw.get("self_id", ""))
            if self_id:
                self.db.execute("UPDATE instances SET self_id=?, updated_at=? WHERE id=?",
                                (self_id, now_iso(), instance_id))
                self.db.execute(
                    "INSERT INTO settings (key,value_json) VALUES (?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                    (f"account:{instance_id}", json.dumps({"uin": self_id}, ensure_ascii=False)),
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
        segments = raw.get("message") or []
        text = _segments_to_text(segments) or str(raw.get("raw_message", ""))[:MAX_TEXT]

        stream = self.db.one(
            "SELECT id FROM streams WHERE instance_id=? AND peer_id=? AND scene=?",
            (instance_id, peer_id, scene),
        )
        if stream:
            stream_id = stream["id"]
            self.db.execute("UPDATE streams SET last_message_at=?, unread=unread+1 WHERE id=?",
                            (now_iso(), stream_id))
        else:
            stream_id = new_id("st")
            title = sender_name if scene == "private" else f"群 {peer_id}"
            self.db.insert("streams", {
                "id": stream_id, "instance_id": instance_id, "scene": scene, "peer_id": peer_id,
                "group_id": group_id, "title": title, "subtitle": "来自协议端的新会话",
                "last_message_at": now_iso(), "unread": 1,
            })

        message = store_message(self.db, stream_id, instance_id, raw.get("message_id"),
                                "in", sender_id, sender_name, segments, text, False, raw)
        self.bus.publish("message.created", message)
        self.db.execute(
            "INSERT INTO stats_daily (date, messages, replies, tokens) VALUES (date('now'), 1, 0, 0) "
            "ON CONFLICT(date) DO UPDATE SET messages=messages+1"
        )

        mentioned = _mentions_self(segments, self_id)
        if scene == "private" or mentioned or "风箱" in text:
            await asyncio.sleep(0.4)
            reply = generate(text)
            out_message = store_message(self.db, stream_id, instance_id, None, "out", self_id,
                                        "风箱", [{"type": "text", "text": reply}], reply, True, None)
            self.bus.publish("message.created", out_message)
            self.db.execute("UPDATE stats_daily SET replies=replies+1 WHERE date=date('now')")
            self.db.execute("UPDATE streams SET last_message_at=? WHERE id=?", (now_iso(), stream_id))
            await self.send_action(instance_id, "send_msg", {
                "message_type": scene, "user_id": int(sender_id) if sender_id.isdigit() else sender_id,
                "group_id": int(peer_id) if scene == "group" and peer_id.isdigit() else None,
                "message": [{"type": "text", "data": {"text": reply}}],
            })


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
    return any(seg.get("type") == "at" and str((seg.get("data") or {}).get("qq")) == self_id for seg in segments)


def store_message(db: Database, stream_id: str, instance_id: str, message_id: Any, direction: str,
                  sender_id: str, sender_name: str, segments: list, text: str, is_bot: bool,
                  raw: dict | None) -> dict[str, Any]:
    row = {
        "id": new_id("msg"), "stream_id": stream_id, "instance_id": instance_id,
        "message_id": str(message_id) if message_id is not None else None,
        "direction": direction, "sender_id": sender_id, "sender_name": sender_name,
        "segments_json": json.dumps(segments, ensure_ascii=False), "text": text,
        "is_bot": 1 if is_bot else 0,
        "raw_json": json.dumps(raw, ensure_ascii=False) if raw else None,
        "created_at": now_iso(),
    }
    db.insert("messages", row)
    return {k: v for k, v in row.items() if k != "raw_json"} | {"segments": segments}
