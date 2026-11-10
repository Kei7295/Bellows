"""ORBIT（星轨）OneBot 11 client helpers.

Bellows acts as an OneBot client and connects *outward* to ORBIT's forward
WebSocket, the same direction MaiBot takes. This module keeps the small pieces
that are shared by the connection wizard and the WebSocket manager: URL
normalisation, HTTP action calls (used by the probe and as a send fallback) and
the probe itself.

ORBIT reference endpoints (default port 8787):

    http://127.0.0.1:8787/onebot?access_token=...
    ws://127.0.0.1:8787/onebot/ws?access_token=...
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib import error, parse, request

DEFAULT_TIMEOUT = 4.0


class OrbitError(RuntimeError):
    """Raised when ORBIT cannot be reached or answers with an error."""


def endpoints(base_url: str, access_token: str = "") -> dict[str, str]:
    """Normalize a user supplied ORBIT address into HTTP/WS endpoints.

    Accepts ``127.0.0.1:8787``, ``http://host``, ``ws://host/onebot/ws`` and
    anything in between, preserving an optional path prefix for reverse proxies.
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        raise OrbitError("ORBIT 地址不能为空")
    if not raw.startswith(("http://", "https://", "ws://", "wss://")):
        raw = f"http://{raw}"

    parsed = parse.urlsplit(raw)
    if not parsed.netloc:
        raise OrbitError("ORBIT 地址缺少主机名")
    secure = parsed.scheme.lower() in ("https", "wss")
    path = parsed.path.rstrip("/")
    for suffix in ("/onebot/ws", "/onebot"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    http_scheme = "https" if secure else "http"
    ws_scheme = "wss" if secure else "ws"
    http_url = parse.urlunsplit((http_scheme, parsed.netloc, f"{path}/onebot", "", ""))
    ws_url = parse.urlunsplit((ws_scheme, parsed.netloc, f"{path}/onebot/ws", "", ""))
    if access_token:
        ws_url = f"{ws_url}?{parse.urlencode({'access_token': access_token})}"
    return {
        "base_url": f"{http_scheme}://{parsed.netloc}{path}",
        "http_url": http_url,
        "ws_url": ws_url,
    }


def _action_sync(
    url: str,
    access_token: str,
    action: str,
    params: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(
        {"action": action, "params": params, "echo": f"bellows_{action}"},
        ensure_ascii=False,
    ).encode()
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    if access_token:
        req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode() or "{}")
    except error.HTTPError as exc:
        if exc.code in (401, 403):
            raise OrbitError("ORBIT 鉴权失败，请检查 access_token") from exc
        detail = exc.read().decode(errors="ignore")[:160]
        raise OrbitError(f"ORBIT 返回 HTTP {exc.code}：{detail}") from exc
    except error.URLError as exc:
        raise OrbitError(f"无法连接 ORBIT：{exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise OrbitError(f"ORBIT 请求超时：{exc}") from exc

    if not isinstance(payload, dict):
        raise OrbitError("ORBIT 返回了无法解析的响应")
    if payload.get("status") == "failed" or payload.get("retcode") not in (0, None):
        message = payload.get("message") or f"retcode={payload.get('retcode')}"
        raise OrbitError(f"ORBIT 动作失败：{message}")
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


async def probe(base_url: str, access_token: str) -> dict[str, Any]:
    """Probe ORBIT with real OneBot calls and return account/version details."""
    urls = endpoints(base_url)
    started = time.perf_counter()
    login = await asyncio.to_thread(
        _action_sync, urls["http_url"], access_token, "get_login_info", {}, DEFAULT_TIMEOUT
    )
    latency_ms = max(1, int((time.perf_counter() - started) * 1000))

    status: dict[str, Any] = {}
    version: dict[str, Any] = {}
    try:
        status = await asyncio.to_thread(
            _action_sync, urls["http_url"], access_token, "get_status", {}, DEFAULT_TIMEOUT
        )
    except OrbitError:
        pass
    try:
        version = await asyncio.to_thread(
            _action_sync,
            urls["http_url"],
            access_token,
            "get_version_info",
            {},
            DEFAULT_TIMEOUT,
        )
    except OrbitError:
        pass

    return {
        "ok": True,
        "base_url": urls["base_url"],
        "http_url": urls["http_url"],
        "ws_url": urls["ws_url"],
        "latency_ms": latency_ms,
        "account": {
            "uin": str(login.get("user_id") or ""),
            "nickname": str(login.get("nickname") or ""),
        },
        "status": status,
        "version": version,
    }


async def http_action(
    base_url: str,
    access_token: str,
    action: str,
    params: dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """Send a OneBot action over HTTP; used when the forward WS is down."""
    try:
        urls = endpoints(base_url, access_token)
        await asyncio.to_thread(
            _action_sync, urls["http_url"], access_token, action, params, timeout
        )
        return True
    except (OrbitError, ValueError):
        return False
