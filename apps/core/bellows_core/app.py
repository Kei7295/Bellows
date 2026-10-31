"""FastAPI application for Bellows core (v0.0.1 BETA)."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import BUILD, __version__
from .api_content import router as content_router
from .api_instances import router as instances_router
from .db import Database, now_iso
from .demo import DemoEngine
from .events import EventBus
from .onebot import OneBotManager
from .runtime import Runtime


def _serialize_instance(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    try:
        row["config"] = json.loads(row.pop("config_json") or "{}")
    except json.JSONDecodeError:
        row["config"] = {}
    return row


def _serialize_message(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    try:
        row["segments"] = json.loads(row.pop("segments_json") or "[]")
    except json.JSONDecodeError:
        row["segments"] = []
    row.pop("raw_json", None)
    row["is_bot"] = bool(row.get("is_bot"))
    return row


def _serialize_log(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    try:
        row["detail"] = json.loads(row.pop("detail_json") or "null")
    except json.JSONDecodeError:
        row["detail"] = None
    return row


def _overview(rt: Runtime) -> dict[str, Any]:
    db = rt.db
    instances = [_serialize_instance(r) for r in db.query("SELECT * FROM instances ORDER BY created_at")]
    today = db.one("SELECT * FROM stats_daily WHERE date=date('now')") or {"messages": 0, "replies": 0, "tokens": 0}
    online = sum(1 for i in instances if i["status"] == "online")
    series = db.query("SELECT date, messages, replies, tokens FROM stats_daily ORDER BY date DESC LIMIT 14")
    series.reverse()
    recent = db.query(
        "SELECT m.*, s.title AS stream_title, s.scene AS scene FROM messages m "
        "LEFT JOIN streams s ON s.id=m.stream_id ORDER BY m.created_at DESC LIMIT 8"
    )
    alerts = []
    for inst in instances:
        if inst["status"] == "error":
            alerts.append({"level": "error", "title": f"{inst['name']} 配置不完整",
                           "detail": "endpoint 为空，补齐连接参数后才能握手。", "instance_id": inst["id"]})
        elif inst["status"] == "offline" and inst["mode"] == "reverse_ws":
            alerts.append({"level": "warning", "title": f"{inst['name']} 等待协议端连接",
                           "detail": "在 NapCat / SnowLuma 中开启反向 WS 并填入实例地址。", "instance_id": inst["id"]})
    return {
        "version": __version__,
        "build": BUILD,
        "uptime": rt.uptime,
        "data_dir": str(rt.data_dir),
        "stats": {
            "online_instances": online,
            "total_instances": len(instances),
            "today_messages": today["messages"],
            "today_replies": today["replies"],
            "today_tokens": today["tokens"],
            "streams": db.one("SELECT COUNT(*) AS n FROM streams")["n"],
            "memories": db.one("SELECT COUNT(*) AS n FROM memories")["n"],
        },
        "series": series,
        "instances": instances,
        "recent": [_serialize_message(r) | {"stream_title": r.get("stream_title")} for r in recent],
        "alerts": alerts,
    }


def create_app(data_dir: Path, token: str = "") -> tuple[FastAPI, Runtime]:
    data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(data_dir / "data.db")
    bus = EventBus()
    rt = Runtime(db=db, bus=bus, data_dir=data_dir, token=token)
    manager = OneBotManager(db, bus)
    demo = DemoEngine(db, bus)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.execute("UPDATE instances SET status='offline', latency_ms=NULL "
                   "WHERE mode != 'demo' AND status IN ('online','connecting','degraded')")
        demo.start()
        db.log("info", "core", f"Bellows core {__version__} 启动，数据目录 {data_dir}")
        bus.publish("log.appended", {"level": "info", "source": "core", "message": "Bellows core 已就绪"})
        yield
        await demo.stop()
        db.execute("UPDATE instances SET status='offline', latency_ms=NULL "
                   "WHERE status IN ('online','connecting','degraded')")
        db.log("info", "core", "Bellows core 优雅退出")
        db.conn.close()

    app = FastAPI(title="Bellows Core", version=__version__, lifespan=lifespan)
    app.state.rt = rt
    app.state.onebot = manager

    @app.middleware("http")
    async def check_token(request: Request, call_next):
        if rt.token and request.url.path.startswith("/api") and request.url.path != "/api/health":
            supplied = request.headers.get("authorization", "")
            if supplied.lower().startswith("bearer "):
                supplied = supplied[7:]
            supplied = supplied or request.query_params.get("token", "")
            if supplied != rt.token:
                return JSONResponse({"code": "unauthorized", "message": "Invalid core token"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__, "build": BUILD, "uptime": rt.uptime,
                "data_dir": str(rt.data_dir), "beta": True}

    @app.get("/api/overview")
    async def overview():
        return _overview(rt)

    @app.get("/api/events")
    async def event_info():
        return {"transport": "websocket", "path": "/api/events", "auth": bool(rt.token)}

    @app.websocket("/api/events")
    async def events_ws(ws: WebSocket):
        supplied = ws.headers.get("authorization", "")
        if supplied.lower().startswith("bearer "):
            supplied = supplied[7:]
        supplied = supplied or ws.query_params.get("token", "")
        if rt.token and supplied != rt.token:
            await ws.close(code=1008)
            return
        await ws.accept()
        queue = bus.subscribe()
        await ws.send_text(json.dumps({"type": "core.ready", "ts": 0, "data": {"version": __version__}}))
        try:
            while True:
                try:
                    envelope = await asyncio.wait_for(queue.get(), timeout=25)
                    await ws.send_text(json.dumps(envelope, ensure_ascii=False))
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping", "ts": 0, "data": {}}))
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    @app.websocket("/onebot/v11/ws/{instance_id}")
    async def onebot_ws(ws: WebSocket, instance_id: str):
        inst = db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
        if not inst:
            await ws.close(code=1008)
            return
        auth = ws.headers.get("authorization", "")
        expected = inst["access_token"] or ""
        if expected and not auth.lower().startswith(f"bearer {expected.lower()}"):
            db.log("warn", "onebot", f"实例 {instance_id} 鉴权失败，连接被拒绝", {"instance": instance_id})
            await ws.close(code=1008)
            return
        await manager.accept(instance_id, ws)
        try:
            while True:
                payload = json.loads(await ws.receive_text())
                if isinstance(payload, dict) and payload.get("post_type"):
                    await manager.handle_event(instance_id, payload)
        except WebSocketDisconnect:
            manager.drop(instance_id)
            db.execute("UPDATE instances SET status='offline', latency_ms=NULL, updated_at=? WHERE id=?",
                       (now_iso(), instance_id))
            bus.publish("instance.status", {"id": instance_id, "status": "offline"})
            entry = db.log("warn", "onebot", f"实例 {instance_id} 连接断开", {"instance": instance_id})
            bus.publish("log.appended", entry)
        except Exception as exc:
            manager.drop(instance_id)
            db.execute("UPDATE instances SET status='offline', latency_ms=NULL, updated_at=? WHERE id=?",
                       (now_iso(), instance_id))
            bus.publish("instance.status", {"id": instance_id, "status": "offline"})
            level = "warn" if "not connected" in str(exc) else "error"
            entry = db.log(level, "onebot", f"实例 {instance_id} 连接终止：{exc}", {"instance": instance_id})
            bus.publish("log.appended", entry)

    @app.post("/api/debug/inbound")
    async def debug_inbound(payload: dict[str, Any]):
        instance_id = payload.get("instance_id", "ins_main")
        stream_id = payload.get("stream_id")
        stream = db.one("SELECT * FROM streams WHERE id=?", (stream_id,)) if stream_id else None
        stream = stream or db.one("SELECT * FROM streams WHERE instance_id=? ORDER BY last_message_at DESC LIMIT 1",
                                  (instance_id,))
        if not stream:
            return JSONResponse({"code": "no_stream", "message": "No stream available"}, status_code=404)
        from .onebot import store_message
        text = str(payload.get("text", "风箱，测试一条消息。"))
        msg = store_message(db, stream["id"], instance_id, None, "in",
                            str(payload.get("sender_id", "300111")),
                            str(payload.get("sender_name", "云雀")),
                            [{"type": "text", "text": text}], text, False, None)
        bus.publish("message.created", msg)
        db.execute("INSERT INTO stats_daily (date,messages,replies,tokens) VALUES (date('now'),1,0,0) "
                   "ON CONFLICT(date) DO UPDATE SET messages=messages+1")
        return {"ok": True, "message": msg}

    app.include_router(instances_router)
    app.include_router(content_router)

    @app.get("/api/meta")
    async def meta():
        return {"app": "Bellows", "app_id": "dev.bellows.desktop", "version": __version__,
                "slogan": "协议进风，人格出火。", "build": BUILD}

    # Serve the built SPA when present (production / beta distribution).
    dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        async def root():
            return RedirectResponse("/index.html")

        @app.get("/{path:path}")
        async def spa(path: str):
            candidate = dist / path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app, rt
