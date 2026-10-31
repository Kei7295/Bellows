"""Shared pytest fixtures for the Bellows core API."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "core"))

from bellows_core.app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path):
    """A TestClient backed by an isolated SQLite database."""
    app, _runtime = create_app(tmp_path, token="")
    with TestClient(app) as test_client:
        yield test_client
