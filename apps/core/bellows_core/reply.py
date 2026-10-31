"""BETA demo reply engine.

v0.0.1 does not call a real LLM. This module produces short, deterministic
replies so the message pipeline and console can be demonstrated end to end.
"""

from __future__ import annotations

import random
import re

_FALLBACK = [
    "收到。当前是 BETA 演示回复引擎，真实模型接入将在后续版本开放。",
    "这条消息已经进入管线。触发判定、冷却和落库都正常。",
    "演示模式下我只做简短回应；配置 Provider 后才会走模型生成。",
]

_RULES = [
    (r"在线|状态|跑着|运行", "在线。演示实例连接正常，消息管线和事件推送都在工作。"),
    (r"插件", "插件页已列出 8 个内置插件，BETA 支持启停与权限查看，运行时隔离还没接。"),
    (
        r"日志|报错|错误|排障",
        "日志页可以按级别和来源筛选。当前没有高危错误，只有未握手的警告。",
    ),
    (r"记忆", "记忆页的条目可以删除。自动抽取和向量检索在 BETA 之后接入。"),
    (
        r"模型|token|Token|成本",
        "模型页可以配置 Provider。BETA 不会真实请求模型，因此不会产生 Token 消耗。",
    ),
    (
        r"反向|握手|ws|WS|NapCat|SnowLuma",
        "反向 WS 路径按实例隔离，协议端连上后状态会从 connecting 变为 online。",
    ),
    (r"ping", "pong。管线延迟在演示模式下低于 50ms。"),
    (r"你好|在吗|hi|hello", "在。风箱演示实例在线，可以直接发消息测试。"),
]


def generate(text: str, persona: str = "风箱管家") -> str:
    clean = text.strip()
    for pattern, answer in _RULES:
        if re.search(pattern, clean, re.IGNORECASE):
            return answer
    if clean.endswith("?"):
        return "这个问题在 BETA 里只能给出演示答案：功能骨架已就绪，真实数据源尚未接入。"
    if len(clean) > 40:
        return "收到这么长的消息。演示引擎不会做长文生成，但分片、限流和落库逻辑已经预留。"
    return random.choice(_FALLBACK)
