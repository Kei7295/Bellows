"""ORBIT forward-WS integration: probe, one-click setup and client pipeline."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websockets
from bellows_core.db import Database, now_iso
from bellows_core.events import EventBus
from bellows_core.onebot import OneBotManager


def _start_http_orbit():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - stdlib naming
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            authorized = self.headers.get("Authorization") == "Bearer orbit-demo-token"
            if not authorized:
                payload = {
                    "status": "failed",
                    "retcode": 1401,
                    "data": None,
                    "message": "access_token 无效或缺失",
                }
                status = 401
            else:
                data = {
                    "get_login_info": {"user_id": 10001, "nickname": "星轨测试号"},
                    "get_status": {"online": True, "good": True},
                    "get_version_info": {
                        "app_name": "ORBIT",
                        "app_version": "0.0.1-beta",
                    },
                }.get(body.get("action"), {})
                payload = {
                    "status": "ok",
                    "retcode": 0,
                    "data": data,
                    "echo": body.get("echo", ""),
                }
                status = 200
            raw = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):  # silence test server
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_orbit_probe_and_auth_error(client):
    server = _start_http_orbit()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        response = client.post(
            "/api/orbit/probe",
            json={"base_url": base, "access_token": "orbit-demo-token"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["account"] == {"uin": "10001", "nickname": "星轨测试号"}
        assert body["ws_url"].endswith("/onebot/ws")
        assert body["version"]["app_version"] == "0.0.1-beta"

        denied = client.post(
            "/api/orbit/probe",
            json={"base_url": base, "access_token": "wrong-token"},
        )
        assert denied.status_code == 502
        assert "鉴权" in denied.json()["message"]
    finally:
        server.shutdown()


def test_orbit_connect_creates_and_reuses_instance(client):
    server = _start_http_orbit()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        created = client.post(
            "/api/orbit/connect",
            json={
                "base_url": base,
                "access_token": "orbit-demo-token",
                "auto_connect": False,
            },
        )
        assert created.status_code == 200
        body = created.json()
        instance = body["instance"]
        assert instance["mode"] == "forward_ws"
        assert instance["self_id"] == "10001"
        assert instance["config"]["protocol"] == "ORBIT"
        assert instance["endpoint"].startswith("ws://")

        again = client.post(
            "/api/orbit/connect",
            json={
                "base_url": base,
                "access_token": "orbit-demo-token",
                "auto_connect": False,
            },
        )
        assert again.json()["instance"]["id"] == instance["id"]

        connected = client.post(f"/api/instances/{instance['id']}/connect").json()
        assert connected["status"] == "connecting"
        client.post(f"/api/instances/{instance['id']}/disconnect")
    finally:
        server.shutdown()


def test_forward_client_receives_and_replies(tmp_path: Path):
    asyncio.run(_forward_scenario(tmp_path))


async def _forward_scenario(tmp_path: Path) -> None:
    received: list[dict] = []
    replied = asyncio.Event()

    async def handler(ws):
        await ws.send(
            json.dumps(
                {
                    "post_type": "meta_event",
                    "meta_event_type": "lifecycle",
                    "self_id": 10001,
                    "time": 0,
                    "status": {"online": True},
                }
            )
        )
        await ws.send(
            json.dumps(
                {
                    "post_type": "message",
                    "message_type": "private",
                    "self_id": 10001,
                    "user_id": 300111,
                    "message_id": "m1",
                    "message": "风箱，你好",
                    "raw_message": "风箱，你好",
                    "sender": {"user_id": 300111, "nickname": "云雀"},
                    "time": 0,
                }
            )
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except Exception:
                return
            payload = json.loads(raw)
            received.append(payload)
            if payload.get("action") == "send_msg":
                await ws.send(
                    json.dumps(
                        {
                            "status": "ok",
                            "retcode": 0,
                            "data": {"message_id": "out1"},
                            "echo": payload.get("echo", ""),
                        }
                    )
                )
                replied.set()
                return

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        db = Database(tmp_path / "orbit.db")
        bus = EventBus()
        manager = OneBotManager(db, bus)
        t = now_iso()
        db.insert(
            "instances",
            {
                "id": "ins_orbit_test",
                "name": "ORBIT 测试",
                "platform": "qq",
                "self_id": "",
                "mode": "forward_ws",
                "endpoint": f"ws://127.0.0.1:{port}/onebot/ws",
                "access_token": "orbit-demo-token",
                "status": "offline",
                "latency_ms": None,
                "config_json": '{"protocol":"ORBIT","auto_reconnect":true}',
                "created_at": t,
                "updated_at": t,
            },
        )
        started = await manager.start_forward("ins_orbit_test")
        assert started["status"] == "connecting"
        await asyncio.wait_for(replied.wait(), timeout=6)

        rows = db.query("SELECT * FROM messages WHERE instance_id=?", ("ins_orbit_test",))
        assert any(row["direction"] == "in" and row["text"] == "风箱，你好" for row in rows)
        assert any(row["direction"] == "out" for row in rows)
        assert any(item.get("action") == "send_msg" for item in received)

        instance = db.one("SELECT * FROM instances WHERE id=?", ("ins_orbit_test",))
        assert instance["status"] == "online"
        assert instance["self_id"] == "10001"

        await manager.shutdown()
        db.conn.close()
