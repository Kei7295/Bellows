"""Health, meta, overview and token middleware."""

from __future__ import annotations

from bellows_core.app import create_app
from fastapi.testclient import TestClient


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["beta"] is True
    assert body["version"] and body["build"]
    assert body["data_dir"]


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["app"] == "Bellows"
    assert body["slogan"] == "协议进风，人格出火。"


def test_overview_shape(client):
    body = client.get("/api/overview").json()
    assert {
        "version",
        "build",
        "uptime",
        "data_dir",
        "stats",
        "series",
        "instances",
        "recent",
        "alerts",
    } <= set(body)
    assert body["stats"]["total_instances"] >= 3
    assert len(body["series"]) <= 14
    assert isinstance(body["alerts"], list)


def test_token_protects_api(tmp_path):
    app, _runtime = create_app(tmp_path, token="secret")
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/instances").status_code == 401
        ok = client.get("/api/instances", headers={"Authorization": "Bearer secret"})
        assert ok.status_code == 200
