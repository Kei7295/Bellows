"""SQLite storage for Bellows v0.0.1 BETA.

Single-file SQLite with WAL. We keep the repository layer deliberately small:
the beta only needs instances, streams, messages, personas, providers,
memories, plugins, logs and settings.
"""

from __future__ import annotations

import json
import random
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS instances (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL DEFAULT 'qq',
  self_id TEXT NOT NULL DEFAULT '', mode TEXT NOT NULL DEFAULT 'reverse_ws',
  endpoint TEXT NOT NULL DEFAULT '', access_token TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'offline', latency_ms INTEGER,
  config_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS streams (
  id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, scene TEXT NOT NULL,
  peer_id TEXT NOT NULL, group_id TEXT, title TEXT NOT NULL, subtitle TEXT,
  last_message_at TEXT, unread INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, stream_id TEXT NOT NULL, instance_id TEXT NOT NULL,
  message_id TEXT, direction TEXT NOT NULL, sender_id TEXT, sender_name TEXT,
  segments_json TEXT NOT NULL DEFAULT '[]', text TEXT NOT NULL DEFAULT '',
  is_bot INTEGER NOT NULL DEFAULT 0, raw_json TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_stream ON messages(stream_id, created_at);
CREATE TABLE IF NOT EXISTS personas (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
  prompt TEXT NOT NULL, style_json TEXT NOT NULL DEFAULT '{}',
  scope TEXT NOT NULL DEFAULT 'global', enabled INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS providers (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
  base_url TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
  params_json TEXT NOT NULL DEFAULT '{}', secret_ref TEXT NOT NULL DEFAULT '',
  enabled INTEGER NOT NULL DEFAULT 1, last_test TEXT, latency_ms INTEGER,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, owner_id TEXT, owner_name TEXT,
  text TEXT NOT NULL, importance INTEGER NOT NULL DEFAULT 3,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plugins (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL,
  author TEXT NOT NULL, description TEXT, trust TEXT NOT NULL DEFAULT 'builtin',
  status TEXT NOT NULL DEFAULT 'active', permissions_json TEXT NOT NULL DEFAULT '[]',
  installed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT NOT NULL, source TEXT NOT NULL,
  message TEXT NOT NULL, detail_json TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
CREATE TABLE IF NOT EXISTS stats_daily (
  date TEXT PRIMARY KEY, messages INTEGER NOT NULL DEFAULT 0,
  replies INTEGER NOT NULL DEFAULT 0, tokens INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY, value_json TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds").replace("+00:00", "Z")


def _day(offset: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self._seed_if_empty()

    # -- helpers ---------------------------------------------------------
    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.lastrowid or 0

    def insert(self, table: str, data: dict[str, Any]) -> None:
        cols = ", ".join(data.keys())
        marks = ", ".join(["?"] * len(data))
        self.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()))

    def update(self, table: str, row_id: str, data: dict[str, Any]) -> None:
        sets = ", ".join(f"{k}=?" for k in data)
        self.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), row_id))

    def log(self, level: str, source: str, message: str, detail: Any = None) -> dict[str, Any]:
        entry = {
            "level": level,
            "source": source,
            "message": message,
            "detail_json": json.dumps(detail, ensure_ascii=False) if detail is not None else None,
            "created_at": now_iso(),
        }
        rid = self.execute(
            "INSERT INTO logs (level, source, message, detail_json, created_at) VALUES (?,?,?,?,?)",
            (entry["level"], entry["source"], entry["message"], entry["detail_json"], entry["created_at"]),
        )
        entry["id"] = rid
        entry["detail"] = detail
        return entry

    def setting(self, key: str, default: Any = None) -> Any:
        row = self.one("SELECT value_json FROM settings WHERE key=?", (key,))
        if not row:
            return default
        try:
            return json.loads(row["value_json"])
        except json.JSONDecodeError:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        self.execute(
            "INSERT INTO settings (key, value_json) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
            (key, json.dumps(value, ensure_ascii=False)),
        )

    # -- seed ------------------------------------------------------------
    def _seed_if_empty(self) -> None:
        if self.one("SELECT id FROM instances LIMIT 1"):
            return
        rnd = random.Random(20261031)
        t = now_iso()
        instances = [
            dict(id="ins_main", name="风箱主号 · 10001", platform="qq", self_id="10001", mode="demo",
                 endpoint="127.0.0.1:6199", access_token="", status="online", latency_ms=24,
                 config_json=json.dumps({"protocol": "NapCat", "auto_reconnect": True}, ensure_ascii=False),
                 created_at=_ago(2400), updated_at=t),
            dict(id="ins_second", name="测试号 · SnowLuma", platform="qq", self_id="10002", mode="reverse_ws",
                 endpoint="ws://127.0.0.1:6199/onebot/v11/ws/ins_second", access_token="beta-token",
                 status="offline", latency_ms=None,
                 config_json=json.dumps({"protocol": "SnowLuma", "auto_reconnect": True}, ensure_ascii=False),
                 created_at=_ago(1800), updated_at=t),
            dict(id="ins_channel", name="频道预留实例", platform="qq", self_id="", mode="forward_ws",
                 endpoint="", access_token="", status="error", latency_ms=None,
                 config_json=json.dumps({"protocol": "未配置", "auto_reconnect": False}, ensure_ascii=False),
                 created_at=_ago(900), updated_at=t),
        ]
        for row in instances:
            self.insert("instances", row)

        streams = [
            dict(id="st_main_group", instance_id="ins_main", scene="group", peer_id="778899001", group_id="778899001",
                 title="风箱内测群", subtitle="47 位成员 · 自动回复已开启", last_message_at=_ago(2), unread=3),
            dict(id="st_tools", instance_id="ins_main", scene="group", peer_id="667788002", group_id="667788002",
                 title="工具链讨论组", subtitle="18 位成员 · 仅 @ 触发", last_message_at=_ago(26), unread=0),
            dict(id="st_lounge", instance_id="ins_main", scene="group", peer_id="556677003", group_id="556677003",
                 title="摸鱼办事处", subtitle="96 位成员 · 触发词模式", last_message_at=_ago(68), unread=1),
            dict(id="st_private_alan", instance_id="ins_main", scene="private", peer_id="200301", group_id=None,
                 title="阿岚", subtitle="私聊 · 白名单", last_message_at=_ago(12), unread=2),
            dict(id="st_private_mu", instance_id="ins_main", scene="private", peer_id="200302", group_id=None,
                 title="木木", subtitle="私聊 · 白名单", last_message_at=_ago(140), unread=0),
            dict(id="st_second_group", instance_id="ins_second", scene="group", peer_id="889900004", group_id="889900004",
                 title="SnowLuma 灰度群", subtitle="32 位成员 · 实例离线", last_message_at=_ago(300), unread=0),
        ]
        for row in streams:
            self.insert("streams", row)

        pairs = [
            ("st_main_group", "群主", "114514", "风箱，报到一下今天的状态。", 190, True),
            ("st_main_group", "风箱", "10001", "在线。当前接入 1 个协议端，消息管线正常，演示回复模式已启用。", 188, False),
            ("st_main_group", "云雀", "300111", "测试一下 @ 触发，看看能不能收到回复。", 170, True),
            ("st_main_group", "风箱", "10001", "收到了。触发判定命中 @，冷却 10 秒内不会重复回复。", 168, False),
            ("st_main_group", "阿岚", "200301", "插件页现在是空的吗？", 120, True),
            ("st_main_group", "风箱", "10001", "已内置 8 个官方插件占位，v0.0.1 BETA 只开放启停和权限查看。", 118, False),
            ("st_main_group", "木木", "200302", "日志里能看到 LLM 请求吗？", 46, True),
            ("st_main_group", "风箱", "10001", "当前是演示回复引擎，还没有真实模型请求。配置 Provider 后会写入 llm 日志。", 44, False),
            ("st_main_group", "云雀", "300111", "今天群里 300 条消息了，风箱处理得过来吗？", 2, True),

            ("st_tools", "Kaze", "400111", "反向 WS 的路径是按实例隔离的吗？", 300, True),
            ("st_tools", "风箱", "10001", "是。每个实例独立路径 /onebot/v11/ws/<instance_id>，避免多账号串号。", 298, False),
            ("st_tools", "白桦", "400112", "SnowLuma 那边握手要先关掉 ws 逆向下发。", 240, True),
            ("st_tools", "Kaze", "400111", "收到，晚点把配置贴到实例详情里。", 210, True),
            ("st_tools", "风箱", "10001", "连接后会先做能力探测，扩展 API 按能力表降级。", 205, False),
            ("st_tools", "白桦", "400112", "建议把心跳超时做成可配置。", 26, True),

            ("st_lounge", "泡芙", "500111", "触发词模式怎么开？", 600, True),
            ("st_lounge", "风箱", "10001", "实例详情里打开触发词，再把关键词写进规则。默认只开 @ 触发。", 598, False),
            ("st_lounge", "泡芙", "500111", "那全量消息进上下文会不会很贵？", 400, True),
            ("st_lounge", "风箱", "10001", "默认关闭。开启后按概率回复，并且有冷却与预算限制。", 398, False),
            ("st_lounge", "汽水", "500112", "风箱今天在线多久了？", 70, True),
            ("st_lounge", "风箱", "10001", "演示实例从启动起持续在线，心跳延迟 24ms。", 68, False),

            ("st_private_alan", "阿岚", "200301", "在吗，帮我看下实例二为什么离线。", 12, True),
            ("st_private_alan", "风箱", "10001", "实例二配置为反向 WS，需要协议端主动连过来。现在还没收到握手。", 10, False),
            ("st_private_alan", "阿岚", "200301", "NapCat 那边的地址是 ws://127.0.0.1:6199/onebot/v11/ws/ins_second。", 5, True),
            ("st_private_alan", "风箱", "10001", "地址格式正确。确认协议端已启动并开启反向 WS 后点一次重连即可。", 4, False),

            ("st_private_mu", "木木", "200302", "记忆页里的条目可以删吗？", 160, True),
            ("st_private_mu", "风箱", "10001", "可以。v0.0.1 只做展示与删除，自动抽取在后续版本。", 158, False),

            ("st_second_group", "雪花", "600111", "这个实例什么时候能上？", 320, True),
            ("st_second_group", "风箱", "10001", "等 SnowLuma 侧握手完成。当前状态离线，页面会显示修复建议。", 318, False),
        ]
        name_by_stream = {s["id"]: s["title"] for s in streams}
        for sid, sender, sender_id, text, minutes, incoming in pairs:
            self.insert("messages", dict(
                id=new_id("msg"), stream_id=sid, instance_id="ins_main" if sid != "st_second_group" else "ins_second",
                message_id=str(rnd.randint(100000, 999999)), direction="in" if incoming else "out",
                sender_id=sender_id, sender_name=sender,
                segments_json=json.dumps([{"type": "text", "text": text}], ensure_ascii=False),
                text=text, is_bot=0 if incoming else 1, raw_json=None, created_at=_ago(minutes),
            ))
        _ = name_by_stream

        personas = [
            dict(id="per_main", name="风箱管家", description="默认人格：简短、可靠、先给结论",
                 prompt="你是风箱，一个运行在本地的 QQ 群聊助手。回答简短直接，先给结论再给必要细节。不卖萌，不使用表情符号。",
                 style_json=json.dumps({"tone": "冷静", "max_chars": 180, "typing_speed": 28}, ensure_ascii=False),
                 scope="global", enabled=1, updated_at=_ago(500)),
            dict(id="per_night", name="夜班技师", description="排障模式：强调错误码与修复步骤",
                 prompt="你是夜班值守的技术支持。优先复述错误码，给出最多三步修复建议，不确定时明确说明。",
                 style_json=json.dumps({"tone": "严谨", "max_chars": 240, "typing_speed": 20}, ensure_ascii=False),
                 scope="global", enabled=1, updated_at=_ago(320)),
            dict(id="per_guard", name="群规守卫", description="只处理入群欢迎与违规提示",
                 prompt="你负责群规提示。语气克制，不与人争论，只陈述规则与下一步操作。",
                 style_json=json.dumps({"tone": "克制", "max_chars": 120, "typing_speed": 32}, ensure_ascii=False),
                 scope="group", enabled=0, updated_at=_ago(90)),
        ]
        for row in personas:
            self.insert("personas", row)

        providers = [
            dict(id="prv_openai", name="OpenAI 兼容", type="openai-compatible", base_url="https://api.openai.com/v1",
                 model="gpt-4o-mini", params_json=json.dumps({"temperature": 0.6, "max_tokens": 800}, ensure_ascii=False),
                 secret_ref="keychain:openai", enabled=1, last_test=_ago(40), latency_ms=812, updated_at=_ago(40)),
            dict(id="prv_deepseek", name="DeepSeek", type="openai-compatible", base_url="https://api.deepseek.com/v1",
                 model="deepseek-chat", params_json=json.dumps({"temperature": 0.7, "max_tokens": 1024}, ensure_ascii=False),
                 secret_ref="keychain:deepseek", enabled=1, last_test=_ago(120), latency_ms=426, updated_at=_ago(120)),
            dict(id="prv_ollama", name="Ollama 本地", type="ollama", base_url="http://127.0.0.1:11434",
                 model="qwen2.5:7b", params_json=json.dumps({"temperature": 0.5, "max_tokens": 512}, ensure_ascii=False),
                 secret_ref="", enabled=0, last_test=None, latency_ms=None, updated_at=_ago(300)),
        ]
        for row in providers:
            self.insert("providers", row)

        memories = [
            ("mem_1", "group", "778899001", "风箱内测群", "群主偏好先给结论，再列最多三条细节。", 5, 600),
            ("mem_2", "group", "778899001", "风箱内测群", "云雀负责协议端联调，提问常围绕 OneBot 路径与握手。", 4, 480),
            ("mem_3", "group", "667788002", "工具链讨论组", "该群默认只响应 @ 消息，闲聊不进上下文。", 4, 300),
            ("mem_4", "user", "200301", "阿岚", "阿岚使用 SnowLuma，实例二需要协议端侧开启反向 WS。", 3, 700),
            ("mem_5", "group", "556677003", "摸鱼办事处", "泡芙关注成本，回答里应提示 Token 预算。", 3, 200),
            ("mem_6", "user", "200302", "木木", "木木希望记忆条目可随时删除，需明确告知存储位置。", 2, 150),
        ]
        for mid, scope, owner, owner_name, text, imp, minutes in memories:
            self.insert("memories", dict(id=mid, scope=scope, owner_id=owner, owner_name=owner_name,
                                         text=text, importance=imp, created_at=_ago(minutes)))

        plugins = [
            ("bellows.builtin.onebot", "OneBot v11 适配器", "0.0.1", "Bellows", "反向 WS / 正向 WS / HTTP 接入层，内置能力探测。", "builtin", "active", ["net.inbound", "message.read", "send.text"], 900),
            ("bellows.builtin.persona", "人格管理", "0.0.1", "Bellows", "人格编辑、上下文拼装与实例绑定。", "builtin", "active", ["config.read", "message.read"], 880),
            ("bellows.builtin.memory", "长期记忆", "0.0.1", "Bellows", "事实抽取与检索（BETA 仅展示与删除）。", "builtin", "active", ["memory.read", "memory.write"], 860),
            ("bellows.builtin.group-tools", "群管工具", "0.0.1", "Bellows", "欢迎、禁言、关键词与群规提示。", "builtin", "active", ["send.text", "chat.read"], 840),
            ("bellows.builtin.scheduler", "定时任务", "0.0.1", "Bellows", "定时消息与主动提醒（BETA 未启用调度器）。", "builtin", "inactive", ["send.text"], 720),
            ("bellows.builtin.web-search", "联网搜索", "0.0.1", "Bellows", "为模型提供搜索工具，需要 net.outbound 白名单。", "builtin", "inactive", ["net.outbound", "llm.invoke"], 700),
            ("bellows.builtin.mcp-bridge", "MCP 桥接", "0.0.1", "Bellows", "把外部 MCP 服务的工具注册进工具表。", "builtin", "inactive", ["net.outbound", "tool.invoke"], 680),
            ("bellows.builtin.diagnostics", "诊断包导出", "0.0.1", "Bellows", "汇总日志、配置与连接快照，脱敏后导出。", "builtin", "active", ["config.read", "audit.read"], 660),
        ]
        for pid, name, ver, author, desc, trust, status, perms, minutes in plugins:
            self.insert("plugins", dict(id=pid, name=name, version=ver, author=author, description=desc,
                                        trust=trust, status=status,
                                        permissions_json=json.dumps(perms, ensure_ascii=False),
                                        installed_at=_ago(minutes)))

        base = datetime.now(timezone.utc).date()
        for offset in range(13, -1, -1):
            day = (base - timedelta(days=offset)).isoformat()
            if offset == 0:
                messages, replies = 342, 128
            else:
                messages = rnd.randint(90, 420)
                replies = int(messages * rnd.uniform(0.28, 0.44))
            self.insert("stats_daily", dict(date=day, messages=messages, replies=replies,
                                            tokens=messages * rnd.randint(38, 96)))

        logs = [
            ("info", "core", "Bellows core 启动完成，监听 127.0.0.1:7801", None, 0),
            ("info", "onebot", "实例 ins_main 演示管线已就绪", {"instance": "ins_main"}, 1),
            ("warn", "onebot", "实例 ins_second 未收到协议端握手，等待反向 WS 连接", {"instance": "ins_second"}, 2),
            ("error", "onebot", "实例 ins_channel 配置不完整：endpoint 为空", {"instance": "ins_channel"}, 3),
            ("info", "message", "入库消息 8 条，触发冷却跳过 1 条", {"stream": "st_main_group"}, 8),
            ("info", "provider", "Provider prv_deepseek 连通性测试通过，延迟 426ms", {"provider": "prv_deepseek"}, 12),
            ("warn", "provider", "Provider prv_ollama 已禁用，未参与路由", {"provider": "prv_ollama"}, 20),
            ("info", "plugin", "内置插件 bellows.builtin.diagnostics 已加载", {"plugin": "bellows.builtin.diagnostics"}, 25),
            ("info", "audit", "读取插件列表（8 项）", {"actor": "local-ui"}, 30),
            ("info", "core", "SQLite WAL checkpoint 完成", None, 45),
        ]
        for level, source, message, detail, minutes in logs:
            self.insert("logs", dict(level=level, source=source, message=message,
                                     detail_json=json.dumps(detail, ensure_ascii=False) if detail else None,
                                     created_at=_ago(minutes)))

        self.set_setting("appearance", {"theme": "system", "density": "comfortable", "animations": True})
        self.set_setting("general", {"launch_at_login": False, "close_to_tray": True, "minimize_on_close": False})
        self.set_setting("triggers", {"group_at": True, "group_keyword": False, "private_whitelist": True, "cooldown": 10})
