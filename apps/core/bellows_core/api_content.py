"""Persona, provider, memory, plugin, log and settings API."""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .db import new_id, now_iso

router = APIRouter(prefix="/api")


def rt_of(request: Request):
    return request.app.state.rt


class PersonaIn(BaseModel):
    name: str
    description: str = ""
    prompt: str = ""
    scope: str = "global"
    enabled: bool = True
    style: dict[str, Any] = {}


class ProviderIn(BaseModel):
    name: str
    type: str = "openai-compatible"
    base_url: str = ""
    model: str = ""
    enabled: bool = True
    params: dict[str, Any] = {}


class PluginToggle(BaseModel):
    enabled: bool


@router.get("/personas")
async def personas(request: Request):
    db = rt_of(request).db
    rows = db.query("SELECT * FROM personas ORDER BY updated_at DESC")
    out = []
    for r in rows:
        r = dict(r)
        try:
            r["style"] = json.loads(r.pop("style_json") or "{}")
        except json.JSONDecodeError:
            r["style"] = {}
        r["enabled"] = bool(r["enabled"])
        out.append(r)
    return out


@router.post("/personas")
async def create_persona(request: Request, payload: PersonaIn):
    rt = rt_of(request)
    pid = new_id("per")
    rt.db.insert(
        "personas",
        {
            "id": pid,
            "name": payload.name,
            "description": payload.description,
            "prompt": payload.prompt,
            "style_json": json.dumps(payload.style, ensure_ascii=False),
            "scope": payload.scope,
            "enabled": 1 if payload.enabled else 0,
            "updated_at": now_iso(),
        },
    )
    entry = rt.db.log("info", "persona", f"创建人格 {payload.name}", {"persona": pid})
    rt.bus.publish("log.appended", entry)
    return {"id": pid, "ok": True}


@router.patch("/personas/{persona_id}")
async def update_persona(request: Request, persona_id: str, payload: dict[str, Any]):
    rt = rt_of(request)
    data: dict[str, Any] = {}
    for key in ("name", "description", "prompt", "scope"):
        if key in payload:
            data[key] = payload[key]
    if "enabled" in payload:
        data["enabled"] = 1 if payload["enabled"] else 0
    if "style" in payload:
        data["style_json"] = json.dumps(payload["style"], ensure_ascii=False)
    if not data:
        return {"ok": True}
    data["updated_at"] = now_iso()
    sets = ", ".join(f"{k}=?" for k in data)
    rt.db.execute(f"UPDATE personas SET {sets} WHERE id=?", (*data.values(), persona_id))
    return {"ok": True}


@router.delete("/personas/{persona_id}")
async def delete_persona(request: Request, persona_id: str):
    rt = rt_of(request)
    rt.db.execute("DELETE FROM personas WHERE id=?", (persona_id,))
    entry = rt.db.log("warn", "persona", f"删除人格 {persona_id}", {"persona": persona_id})
    rt.bus.publish("log.appended", entry)
    return {"ok": True}


@router.get("/providers")
async def providers(request: Request):
    db = rt_of(request).db
    rows = db.query("SELECT * FROM providers ORDER BY updated_at DESC")
    out = []
    for r in rows:
        r = dict(r)
        r["params"] = json.loads(r.pop("params_json") or "{}")
        r["enabled"] = bool(r["enabled"])
        r["has_key"] = bool(r["secret_ref"])
        out.append(r)
    return out


@router.post("/providers")
async def create_provider(request: Request, payload: ProviderIn):
    rt = rt_of(request)
    pid = new_id("prv")
    rt.db.insert(
        "providers",
        {
            "id": pid,
            "name": payload.name,
            "type": payload.type,
            "base_url": payload.base_url,
            "model": payload.model,
            "params_json": json.dumps(payload.params, ensure_ascii=False),
            "secret_ref": "",
            "enabled": 1 if payload.enabled else 0,
            "last_test": None,
            "latency_ms": None,
            "updated_at": now_iso(),
        },
    )
    entry = rt.db.log("info", "provider", f"创建 Provider {payload.name}", {"provider": pid})
    rt.bus.publish("log.appended", entry)
    return {"id": pid, "ok": True}


@router.patch("/providers/{provider_id}")
async def update_provider(request: Request, provider_id: str, payload: dict[str, Any]):
    rt = rt_of(request)
    data: dict[str, Any] = {}
    for key in ("name", "type", "base_url", "model"):
        if key in payload:
            data[key] = payload[key]
    if "enabled" in payload:
        data["enabled"] = 1 if payload["enabled"] else 0
    if "params" in payload:
        data["params_json"] = json.dumps(payload["params"], ensure_ascii=False)
    if not data:
        return {"ok": True}
    data["updated_at"] = now_iso()
    sets = ", ".join(f"{k}=?" for k in data)
    rt.db.execute(f"UPDATE providers SET {sets} WHERE id=?", (*data.values(), provider_id))
    return {"ok": True}


@router.delete("/providers/{provider_id}")
async def delete_provider(request: Request, provider_id: str):
    rt = rt_of(request)
    rt.db.execute("DELETE FROM providers WHERE id=?", (provider_id,))
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(request: Request, provider_id: str):
    rt = rt_of(request)
    inst = rt.db.one("SELECT * FROM providers WHERE id=?", (provider_id,))
    if not inst:
        return JSONResponse({"code": "not_found", "message": "Provider not found"}, status_code=404)
    # BETA: simulated connectivity probe, no external request is made.
    await asyncio.sleep(0.5)
    latency = random.randint(180, 900)
    rt.db.execute(
        "UPDATE providers SET last_test=?, latency_ms=?, updated_at=? WHERE id=?",
        (now_iso(), latency, now_iso(), provider_id),
    )
    entry = rt.db.log(
        "info",
        "provider",
        f"Provider {inst['name']} 连通性测试通过（模拟），{latency}ms",
        {"provider": provider_id},
    )
    rt.bus.publish("log.appended", entry)
    return {
        "ok": True,
        "latency_ms": latency,
        "mode": "simulated",
        "message": "BETA 使用模拟探测，未发起真实请求",
    }


@router.get("/memories")
async def memories(request: Request, q: str | None = None, scope: str | None = None):
    db = rt_of(request).db
    sql = "SELECT * FROM memories WHERE 1=1"
    params: list[Any] = []
    if q:
        sql += " AND text LIKE ?"
        params.append(f"%{q}%")
    if scope:
        sql += " AND scope=?"
        params.append(scope)
    sql += " ORDER BY created_at DESC"
    return db.query(sql, tuple(params))


@router.delete("/memories/{memory_id}")
async def delete_memory(request: Request, memory_id: str):
    rt = rt_of(request)
    rt.db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
    entry = rt.db.log("warn", "memory", "删除记忆条目", {"memory": memory_id})
    rt.bus.publish("log.appended", entry)
    return {"ok": True}


@router.get("/plugins")
async def plugins(request: Request):
    db = rt_of(request).db
    rows = db.query("SELECT * FROM plugins ORDER BY installed_at DESC")
    out = []
    for r in rows:
        r = dict(r)
        r["permissions"] = json.loads(r.pop("permissions_json") or "[]")
        out.append(r)
    return out


@router.post("/plugins/{plugin_id}/toggle")
async def toggle_plugin(request: Request, plugin_id: str, payload: PluginToggle):
    rt = rt_of(request)
    status = "active" if payload.enabled else "inactive"
    rt.db.execute("UPDATE plugins SET status=? WHERE id=?", (status, plugin_id))
    entry = rt.db.log(
        "info", "plugin", f"插件 {plugin_id} 状态切换为 {status}", {"plugin": plugin_id}
    )
    rt.bus.publish("log.appended", entry)
    return {"ok": True, "status": status}


@router.post("/plugins/{plugin_id}/reload")
async def reload_plugin(request: Request, plugin_id: str):
    rt = rt_of(request)
    entry = rt.db.log(
        "warn",
        "plugin",
        "插件运行时在 v0.0.1 BETA 尚未实现，无法热重载",
        {"plugin": plugin_id},
    )
    rt.bus.publish("log.appended", entry)
    return {"ok": False, "message": "BETA 暂不支持热重载，插件运行时将在后续版本接入"}


@router.get("/plugins/market")
async def plugin_market():
    return {
        "status": "readonly-preview",
        "updated_at": now_iso(),
        "items": [
            {
                "id": "bellows.example.echo",
                "name": "Echo 示例",
                "version": "0.1.0",
                "author": "Bellows",
                "description": "最小插件模板：注册一个命令并回显文本。",
                "permissions": ["send.text", "config.read"],
            },
            {
                "id": "bellows.example.weather",
                "name": "天气查询",
                "version": "0.1.0",
                "author": "Bellows",
                "description": "示例：通过白名单域名请求天气并格式化为文本。",
                "permissions": ["net.outbound"],
            },
            {
                "id": "bellows.example.digest",
                "name": "群聊摘要",
                "version": "0.1.0",
                "author": "Bellows",
                "description": "示例：按时间窗口汇总群消息。",
                "permissions": ["message.read", "send.text"],
            },
        ],
        "note": "v0.0.1 BETA 的市场为只读预览，安装流程尚未开放。",
    }


@router.get("/logs")
async def logs(
    request: Request,
    level: str | None = None,
    source: str | None = None,
    q: str | None = None,
    limit: int = 100,
):
    db = rt_of(request).db
    sql = "SELECT * FROM logs WHERE 1=1"
    params: list[Any] = []
    if level:
        sql += " AND level=?"
        params.append(level)
    if source:
        sql += " AND source=?"
        params.append(source)
    if q:
        sql += " AND message LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    out = []
    for r in db.query(sql, tuple(params)):
        try:
            r["detail"] = json.loads(r.pop("detail_json") or "null")
        except json.JSONDecodeError:
            r["detail"] = None
        out.append(r)
    return out


@router.get("/audit")
async def audit(request: Request, limit: int = 60):
    db = rt_of(request).db
    rows = db.query(
        "SELECT * FROM logs WHERE source IN ('audit','instance','plugin','persona','memory') "
        "ORDER BY created_at DESC LIMIT ?",
        (max(1, min(limit, 200)),),
    )
    return rows


@router.get("/settings")
async def get_settings(request: Request):
    db = rt_of(request).db
    return {
        r["key"]: json.loads(r["value_json"])
        for r in db.query("SELECT * FROM settings")
        if not r["key"].startswith("account:")
    }


@router.put("/settings")
async def put_settings(request: Request, payload: dict[str, Any]):
    rt = rt_of(request)
    for key, value in payload.items():
        rt.db.set_setting(key, value)
    entry = rt.db.log(
        "info",
        "settings",
        f"更新设置：{', '.join(payload.keys())}",
        {"keys": list(payload.keys())},
    )
    rt.bus.publish("log.appended", entry)
    return {
        "ok": True,
        "settings": {
            r["key"]: json.loads(r["value_json"])
            for r in rt.db.query("SELECT * FROM settings")
            if not r["key"].startswith("account:")
        },
    }
