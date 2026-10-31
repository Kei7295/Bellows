"""Instance CRUD, streams and message flow."""

from __future__ import annotations


def test_instance_crud(client):
    created = client.post("/api/instances", json={"name": "临时实例", "mode": "demo"}).json()
    instance_id = created["id"]
    assert instance_id.startswith("ins_")

    patched = client.patch(f"/api/instances/{instance_id}", json={"name": "改名实例"}).json()
    assert patched["name"] == "改名实例"

    connected = client.post(f"/api/instances/{instance_id}/connect").json()
    assert connected["status"] == "online"

    listed = client.get("/api/instances").json()
    assert any(item["id"] == instance_id for item in listed)

    assert client.delete(f"/api/instances/{instance_id}").json()["ok"] is True
    remaining = client.get("/api/instances").json()
    assert all(item["id"] != instance_id for item in remaining)


def test_unknown_instance_returns_404(client):
    response = client.patch("/api/instances/ins_missing", json={"name": "x"})
    assert response.status_code == 404


def test_streams_and_messages(client):
    streams = client.get("/api/streams").json()
    assert any(item["id"] == "st_main_group" for item in streams)

    messages = client.get("/api/streams/st_main_group/messages", params={"limit": 10}).json()
    assert len(messages) <= 10

    sent = client.post("/api/streams/st_main_group/send", json={"text": "你好，风箱。"}).json()
    assert sent["ok"] is True
    assert sent["message"]["text"] == "你好，风箱。"

    empty = client.post("/api/streams/st_main_group/send", json={"text": "   "})
    assert empty.status_code == 400


def test_debug_inbound(client):
    injected = client.post(
        "/api/debug/inbound",
        json={
            "instance_id": "ins_main",
            "stream_id": "st_main_group",
            "text": "风箱，探针消息。",
        },
    ).json()
    assert injected["ok"] is True

    messages = client.get("/api/streams/st_main_group/messages", params={"limit": 10}).json()
    assert any(item["text"] == "风箱，探针消息。" for item in messages)
