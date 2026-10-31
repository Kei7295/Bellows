"""Personas, providers, plugins, logs and settings."""

from __future__ import annotations


def test_persona_crud(client):
    created = client.post("/api/personas", json={"name": "测试人格", "prompt": "保持简短"}).json()
    persona_id = created["id"]
    assert created["ok"] is True

    personas = client.get("/api/personas").json()
    assert any(item["id"] == persona_id for item in personas)

    assert client.patch(f"/api/personas/{persona_id}", json={"enabled": False}).json()["ok"] is True
    assert client.delete(f"/api/personas/{persona_id}").json()["ok"] is True


def test_provider_probe_is_simulated(client):
    created = client.post(
        "/api/providers",
        json={"name": "本地模拟", "type": "openai-compatible", "model": "demo"},
    ).json()
    provider_id = created["id"]

    probe = client.post(f"/api/providers/{provider_id}/test").json()
    assert probe["ok"] is True
    assert probe["mode"] == "simulated"

    assert client.delete(f"/api/providers/{provider_id}").json()["ok"] is True


def test_plugins_are_readonly_preview(client):
    plugins = client.get("/api/plugins").json()
    assert isinstance(plugins, list) and plugins

    market = client.get("/api/plugins/market").json()
    assert market["status"] == "readonly-preview"

    reloaded = client.post(f"/api/plugins/{plugins[0]['id']}/reload").json()
    assert reloaded["ok"] is False


def test_settings_roundtrip(client):
    saved = client.put("/api/settings", json={"beta_banner": True}).json()
    assert saved["settings"]["beta_banner"] is True
    assert client.get("/api/settings").json()["beta_banner"] is True


def test_logs_and_memories(client):
    logs = client.get("/api/logs").json()
    assert isinstance(logs, list) and logs
    assert any(item["source"] == "core" for item in logs)

    memories = client.get("/api/memories").json()
    assert isinstance(memories, list)
