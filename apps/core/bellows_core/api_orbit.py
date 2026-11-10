"""ORBIT（星轨）onboarding API: probe and one-click forward-WS setup."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api_instances import ser_instance
from .db import new_id, now_iso
from .orbit import OrbitError, endpoints, probe

router = APIRouter(prefix="/api/orbit")


class ProbeIn(BaseModel):
    base_url: str = "http://127.0.0.1:8787"
    access_token: str = ""


class ConnectIn(BaseModel):
    base_url: str = "http://127.0.0.1:8787"
    access_token: str = ""
    name: str = ""
    instance_id: str | None = None
    auto_connect: bool = True


def _find_forward(db: Any, base_url: str) -> dict[str, Any] | None:
    for row in db.query("SELECT id, name, endpoint FROM instances WHERE mode='forward_ws'"):
        try:
            if endpoints(row["endpoint"])["base_url"] == base_url:
                return row
        except OrbitError:
            continue
    return None


@router.post("/probe")
async def orbit_probe(payload: ProbeIn):
    try:
        return await probe(payload.base_url, payload.access_token)
    except OrbitError as exc:
        return JSONResponse({"code": "orbit_unreachable", "message": str(exc)}, status_code=502)


@router.post("/connect")
async def orbit_connect(request: Request, payload: ConnectIn):
    rt = request.app.state.rt
    db = rt.db
    try:
        info = await probe(payload.base_url, payload.access_token)
    except OrbitError as exc:
        return JSONResponse({"code": "orbit_unreachable", "message": str(exc)}, status_code=502)

    uin = str(info["account"].get("uin") or "")
    nickname = str(info["account"].get("nickname") or "")
    config = {"protocol": "ORBIT", "auto_reconnect": True}
    ws_endpoint = endpoints(payload.base_url)["ws_url"]
    t = now_iso()

    row: dict[str, Any] | None = None
    if payload.instance_id:
        row = db.one("SELECT * FROM instances WHERE id=?", (payload.instance_id,))
        if not row:
            return JSONResponse(
                {"code": "not_found", "message": "Instance not found"}, status_code=404
            )
    else:
        row = _find_forward(db, info["base_url"])

    name = (
        payload.name.strip()
        or (row["name"] if row else "")
        or f"ORBIT · {nickname or uin or '星轨'}"
    )

    if row:
        instance_id = row["id"]
        db.execute(
            "UPDATE instances SET name=?, platform='qq', self_id=?, mode='forward_ws', "
            "endpoint=?, access_token=?, status='offline', latency_ms=NULL, "
            "config_json=?, updated_at=? WHERE id=?",
            (
                name,
                uin,
                ws_endpoint,
                payload.access_token,
                json.dumps(config, ensure_ascii=False),
                t,
                instance_id,
            ),
        )
    else:
        instance_id = new_id("ins")
        db.insert(
            "instances",
            {
                "id": instance_id,
                "name": name,
                "platform": "qq",
                "self_id": uin,
                "mode": "forward_ws",
                "endpoint": ws_endpoint,
                "access_token": payload.access_token,
                "status": "offline",
                "latency_ms": None,
                "config_json": json.dumps(config, ensure_ascii=False),
                "created_at": t,
                "updated_at": t,
            },
        )

    db.set_setting(f"account:{instance_id}", {"uin": uin})
    entry = db.log(
        "info",
        "orbit",
        f"接入 ORBIT：{name}（{nickname or uin or '未命名账号'}）",
        {"instance": instance_id},
    )
    rt.bus.publish("log.appended", entry)

    connection: dict[str, Any] | None = None
    if payload.auto_connect:
        connection = await request.app.state.onebot.start_forward(instance_id)

    latest = db.one("SELECT * FROM instances WHERE id=?", (instance_id,))
    return {
        "ok": True,
        "instance": ser_instance(latest) if latest else {},
        "probe": info,
        "connection": connection,
    }
