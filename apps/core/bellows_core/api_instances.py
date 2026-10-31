"""Instance, stream and message API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .db import new_id, now_iso
from .reply import generate

router = APIRouter(prefix="/api")


def rt_of(request: Request):
    return request.app.state.rt


def ser_instance(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    try:
        row["config"] = json.loads(row.pop("config_json") or "{}")
    except json.JSONDecodeError:
        row["config"] = {}
    return row


def ser_message(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    try:
        row["segments"] = json.loads(row.pop("segments_json") or "[]")
    except json.JSONDecodeError:
        row["segments"] = []
    row.pop("raw_json", None)
    row["is_bot"] = bool(row.get("is_bot"))
    return row


class InstanceIn(BaseModel):
    name: str
    mode: str = "reverse_ws"
    endpoint: str = ""
    access_token: str = ""
    self_id: str = ""
    platform: str = "qq"
    protocol: str = "NapCat"


class InstancePatch(BaseModel):
    name: str | None = None
    mode: str | None = None
    endpoint: str | None = None
    access_token: str | None = None
    self_id: str | None = None
    status: str | None = None


class SendIn(BaseModel):
    text: str
    use_ai: bool = False


@router.get("/instances")
async def list_instances(request: Request):
    db = rt_of(request).db
    rows = [ser_instance(r) for r in db.query("SELECT * FROM instances ORDER BY created_at")]
    for row in rows:
        acc = db.setting(f"account:{row['id']}")
        row["account"] = acc
    return rows


@router.post("/instances")
async def create_instance(request: Request, payload: InstanceIn):
    rt = rt_of(request)
    db = rt.db
    iid = new_id("ins")
    t = now_iso()
    db.insert("instances", {
        "id": iid, "name": payload.name, "platform": payload.platform, "self_id": payload.self_id,
        "mode": payload.mode, "endpoint": payload.endpoint, "access_token": payload.access_token,
        "status": "offline", "latency_ms": None,
        "config_json": json.dumps({"protocol": payload.protocol, "auto_reconnect": True}, ensure_ascii=False),
        "created_at": t, "updated_at": t,
    })
    entry = db.log("info", "instance", f"创建实例 {payload.name}", {"instance": iid})
    rt.bus.publish("log.appended", entry)
    row = db.one("SELECT * FROM instances WHERE id=?", (iid,))
    return ser_instance(row) if row else {}


@router.patch("/instances/{instance_id}")
async def update_instance(request: Request, instance_id: str, payload: InstancePatch):
    rt = rt_of(request)
    db = rt.db
    if not db.one("SELECT id FROM instances WHERE id=?", (instance_id,)):
        return JSONResponse({"code": "not_found", "message": "Instance not found"}, status_code=404)
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return ser_instance(db.one("SELECT * FROM instances WHERE id=?", (instance_id,)))
    data["updated_at"] = now_iso()
    sets = ", ".join(f"{k}=?" for k in data)
    db.execute(f"UPDATE instances SET {sets} WHERE id=?", (*data.values(), instance_id))
    return ser_instance(db.one("SELECT * FROM instances WHERE id=?", (instance_id,) ))


@router.delete("/instances/{instance_id}")
async def delete_instance(request: Request, instance_id: str):
    rt = rt_of(request)
    db = rt.db
    db.execute("DELETE FROM messages WHERE instance_id=?", (instance_id,))
    db.execute("DELETE FROM streams WHERE instance_id=?", (instance_id,))
    db.execute("DELETE FROM instances WHERE id=?", (instance_id,))
    entry = db.log("warn", "instance", f"删除实例 {instance_id}", {"instance": instance_id})
    rt.bus.publish("log.appended", entry)
    return {"ok": True}


@router.post("/instances/{instance_id}/connect")
async def connect_instance(request: Request, instance_id: str):
    rt = rt_of(request)
    db = rt.db
    inst = db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
    if not inst:
        return JSONResponse({"code": "not_found", "message": "Instance not found"}, status_code=404)
    if inst["mode"] == "demo":
        db.execute("UPDATE instances SET status='online', latency_ms=24, updated_at=? WHERE id=?",
                   (now_iso(), instance_id))
        status = "online"
        msg = f"演示实例 {inst['name']} 已上线"
        level = "info"
    elif inst["mode"] == "reverse_ws":
        db.execute("UPDATE instances SET status='connecting', updated_at=? WHERE id=?",
                   (now_iso(), instance_id))
        status = "connecting"
        msg = f"实例 {inst['name']} 等待协议端反向 WS 握手"
        level = "info"
    else:
        db.execute("UPDATE instances SET status='error', updated_at=? WHERE id=?",
                   (now_iso(), instance_id))
        status = "error"
        msg = "正向 WS / HTTP 模式在 v0.0.1 BETA 尚未启用"
        level = "warn"
    rt.bus.publish("instance.status", {"id": instance_id, "status": status})
    entry = db.log(level, "instance", msg, {"instance": instance_id})
    rt.bus.publish("log.appended", entry)
    return {"ok": True, "status": status, "message": msg}


@router.post("/instances/{instance_id}/disconnect")
async def disconnect_instance(request: Request, instance_id: str):
    rt = rt_of(request)
    await request.app.state.onebot.disconnect(instance_id)
    rt.db.execute("UPDATE instances SET status='offline', latency_ms=NULL, updated_at=? WHERE id=?",
                  (now_iso(), instance_id))
    rt.bus.publish("instance.status", {"id": instance_id, "status": "offline"})
    entry = rt.db.log("info", "instance", f"实例 {instance_id} 已断开", {"instance": instance_id})
    rt.bus.publish("log.appended", entry)
    return {"ok": True, "status": "offline"}


@router.get("/instances/{instance_id}/capabilities")
async def capabilities(request: Request, instance_id: str):
    rt = rt_of(request)
    inst = rt.db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
    if not inst:
        return JSONResponse({"code": "not_found", "message": "Instance not found"}, status_code=404)
    caps = {
        "send_private_msg": True, "send_group_msg": True, "delete_msg": True,
        "get_group_list": True, "get_friend_list": True, "set_group_ban": True,
        "send_group_forward_msg": inst["mode"] != "demo", "guild": False,
    }
    return {"instance_id": instance_id, "probed_at": now_iso(), "capabilities": caps,
            "protocol": inst["config_json"] and json.loads(inst["config_json"]).get("protocol")}


@router.get("/streams")
async def list_streams(request: Request, instance_id: str | None = None, scene: str | None = None, q: str | None = None):
    db = rt_of(request).db
    sql = ("SELECT s.*, (SELECT text FROM messages m WHERE m.stream_id=s.id ORDER BY m.created_at DESC LIMIT 1) "
           "AS last_text, (SELECT sender_name FROM messages m WHERE m.stream_id=s.id ORDER BY m.created_at DESC LIMIT 1) "
           "AS last_sender FROM streams s WHERE 1=1")
    params: list[Any] = []
    if instance_id:
        sql += " AND s.instance_id=?"
        params.append(instance_id)
    if scene:
        sql += " AND s.scene=?"
        params.append(scene)
    if q:
        sql += " AND (s.title LIKE ? OR s.peer_id LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    sql += " ORDER BY s.last_message_at DESC"
    return db.query(sql, tuple(params))


@router.get("/streams/{stream_id}")
async def stream_detail(request: Request, stream_id: str):
    db = rt_of(request).db
    stream = db.one("SELECT * FROM streams WHERE id=?", (stream_id,))
    if not stream:
        return JSONResponse({"code": "not_found", "message": "Stream not found"}, status_code=404)
    count = db.one("SELECT COUNT(*) AS n FROM messages WHERE stream_id=?", (stream_id,))
    return stream | {"message_count": count["n"] if count else 0,
                     "persona": db.one("SELECT name FROM personas WHERE enabled=1 LIMIT 1")}


@router.get("/streams/{stream_id}/messages")
async def stream_messages(request: Request, stream_id: str, limit: int = 80, before: str | None = None):
    db = rt_of(request).db
    limit = max(1, min(limit, 300))
    sql = "SELECT * FROM messages WHERE stream_id=?"
    params: list[Any] = [stream_id]
    if before:
        sql += " AND created_at < ?"
        params.append(before)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.query(sql, tuple(params))
    rows.reverse()
    return [ser_message(r) for r in rows]


@router.get("/streams/{stream_id}/messages/raw/{message_id}")
async def raw_message(request: Request, stream_id: str, message_id: str):
    db = rt_of(request).db
    row = db.one("SELECT * FROM messages WHERE id=?", (message_id,))
    if not row:
        return JSONResponse({"code": "not_found", "message": "Message not found"}, status_code=404)
    return {"message": ser_message(row), "raw": json.loads(row["raw_json"] or "null")}


@router.post("/streams/{stream_id}/send")
async def send_message(request: Request, stream_id: str, payload: SendIn):
    rt = rt_of(request)
    db = rt.db
    stream = db.one("SELECT * FROM streams WHERE id=?", (stream_id,))
    if not stream:
        return JSONResponse({"code": "not_found", "message": "Stream not found"}, status_code=404)
    text = payload.text.strip()
    if not text:
        return JSONResponse({"code": "empty", "message": "Message text is empty"}, status_code=400)
    t = now_iso()
    mid = new_id("msg")
    row = {
        "id": mid, "stream_id": stream_id, "instance_id": stream["instance_id"], "message_id": None,
        "direction": "out", "sender_id": "10001", "sender_name": "风箱",
        "segments_json": json.dumps([{"type": "text", "text": text}], ensure_ascii=False),
        "text": text, "is_bot": 1, "raw_json": None, "created_at": t,
    }
    db.insert("messages", row)
    db.execute("UPDATE streams SET last_message_at=?, unread=0 WHERE id=?", (t, stream_id))
    db.execute("INSERT INTO stats_daily (date,messages,replies,tokens) VALUES (date('now'),1,1,0) "
               "ON CONFLICT(date) DO UPDATE SET messages=messages+1, replies=replies+1")
    msg = ser_message(row)
    rt.bus.publish("message.created", msg)
    await request.app.state.onebot.send_action(stream["instance_id"], "send_msg", {
        "message_type": stream["scene"], "user_id": stream["peer_id"],
        "group_id": stream["peer_id"] if stream["scene"] == "group" else None,
        "message": [{"type": "text", "data": {"text": text}}],
    })
    entry = db.log("info", "message", f"人工发送到 {stream['title']}", {"stream": stream_id})
    rt.bus.publish("log.appended", entry)

    if payload.use_ai:
        async def ai_reply():
            await asyncio.sleep(1.4)
            reply = generate(text)
            rid = new_id("msg")
            rrow = {
                "id": rid, "stream_id": stream_id, "instance_id": stream["instance_id"], "message_id": None,
                "direction": "out", "sender_id": "10001", "sender_name": "风箱",
                "segments_json": json.dumps([{"type": "text", "text": reply}], ensure_ascii=False),
                "text": reply, "is_bot": 1, "raw_json": None, "created_at": now_iso(),
            }
            db.insert("messages", rrow)
            db.execute("UPDATE streams SET last_message_at=? WHERE id=?", (rrow["created_at"], stream_id))
            db.execute("UPDATE stats_daily SET replies=replies+1 WHERE date=date('now')")
            rt.bus.publish("message.created", ser_message(rrow))
        asyncio.create_task(ai_reply())
    return {"ok": True, "message": msg}
