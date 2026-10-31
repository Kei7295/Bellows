"""Simulated protocol activity for v0.0.1 BETA.

No real QQ connection is required to evaluate the UI: the demo loop produces
inbound messages and occasional replies, and broadcasts the same events a
OneBot reverse-WS connection would emit.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from .db import Database, now_iso
from .events import EventBus
from .onebot import store_message
from .reply import generate

INBOUND = [
    "风箱，现在在线几个实例？",
    "今天消息量比昨天高吗？",
    "帮我把群规提示关掉。",
    "日志里那条 warn 是什么意思？",
    "插件热重载什么时候能上？",
    "控制台能直接接管发送吗？",
    "实例二还是连不上，地址我发你了。",
    "这个版本的 Token 消耗是多少？",
    "群里的冷却时间能改成 30 秒吗？",
    "SnowLuma 握手日志在哪里看？",
    "记忆条目删除后会立即生效吗？",
    "让我看看最近七天的消息趋势。",
]

SENDERS = [
    ("阿岚", "200301"),
    ("木木", "200302"),
    ("云雀", "300111"),
    ("Kaze", "400111"),
    ("泡芙", "500111"),
]


class DemoEngine:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def _demo_instances(self) -> list[dict[str, Any]]:
        return self.db.query("SELECT * FROM instances WHERE mode='demo' AND status='online'")

    async def _loop(self) -> None:
        self._running = True
        rnd = random.Random()
        await asyncio.sleep(6)
        while self._running:
            try:
                await asyncio.sleep(rnd.uniform(11, 18))
                if not self._demo_instances():
                    continue
                if not self.db.setting("demo.enabled", True):
                    continue
                await self._emit_one(rnd)
                await self._heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # keep the demo loop alive
                entry = self.db.log("error", "demo", f"演示管线异常：{exc}")
                self.bus.publish("log.appended", entry)

    async def _emit_one(self, rnd: random.Random) -> None:
        streams = self.db.query(
            "SELECT s.* FROM streams s JOIN instances i ON i.id=s.instance_id "
            "WHERE i.mode='demo' AND i.status='online' ORDER BY s.last_message_at DESC LIMIT 6"
        )
        if not streams:
            return
        stream = rnd.choice(streams)
        sender_name, sender_id = rnd.choice(SENDERS)
        text = rnd.choice(INBOUND)
        message = store_message(
            self.db,
            stream["id"],
            stream["instance_id"],
            None,
            "in",
            sender_id,
            sender_name,
            [{"type": "text", "text": text}],
            text,
            False,
            None,
        )
        self.db.execute(
            "UPDATE streams SET last_message_at=?, unread=unread+1 WHERE id=?",
            (now_iso(), stream["id"]),
        )
        self.db.execute(
            "INSERT INTO stats_daily (date, messages, replies, tokens) VALUES (date('now'), 1, 0, 0) "
            "ON CONFLICT(date) DO UPDATE SET messages=messages+1"
        )
        self.bus.publish("message.created", message)
        self.bus.publish(
            "stream.updated",
            {"id": stream["id"], "last_message_at": message["created_at"]},
        )

        if "风箱" in text or text.endswith("吗？") or text.endswith("？"):
            await asyncio.sleep(1.0)
            reply = generate(text)
            out = store_message(
                self.db,
                stream["id"],
                stream["instance_id"],
                None,
                "out",
                "10001",
                "风箱",
                [{"type": "text", "text": reply}],
                reply,
                True,
                None,
            )
            self.db.execute(
                "UPDATE streams SET last_message_at=? WHERE id=?",
                (now_iso(), stream["id"]),
            )
            self.db.execute("UPDATE stats_daily SET replies=replies+1 WHERE date=date('now')")
            self.bus.publish("message.created", out)

    async def _heartbeat(self) -> None:
        rows = self._demo_instances()
        for inst in rows:
            latency = random.randint(14, 42)
            self.db.execute(
                "UPDATE instances SET latency_ms=?, updated_at=? WHERE id=?",
                (latency, now_iso(), inst["id"]),
            )
            self.bus.publish(
                "instance.status",
                {"id": inst["id"], "status": "online", "latency_ms": latency},
            )
        overview = self.db.one(
            "SELECT COALESCE(SUM(messages),0) AS messages, COALESCE(SUM(replies),0) AS replies "
            "FROM stats_daily WHERE date=date('now')"
        )
        self.bus.publish(
            "stats.tick",
            {
                "messages": overview["messages"] if overview else 0,
                "replies": overview["replies"] if overview else 0,
            },
        )
