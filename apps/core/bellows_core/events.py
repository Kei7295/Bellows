"""In-process event bus used by the REST/WS API and the demo pipeline."""

from __future__ import annotations

import asyncio
import time
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, kind: str, data: Any) -> None:
        envelope = {"type": kind, "ts": int(time.time() * 1000), "data": data}
        for q in list(self._subscribers):
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                pass
