"""Shared runtime context for the BETA core."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import Database
from .events import EventBus


@dataclass
class Runtime:
    db: Database
    bus: EventBus
    data_dir: Path
    started_at: float = field(default_factory=time.time)
    token: str = ""
    online: dict[str, Any] = field(default_factory=dict)

    @property
    def uptime(self) -> int:
        return int(time.time() - self.started_at)
