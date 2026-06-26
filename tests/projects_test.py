"""Save shelf + persisted transcripts."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        r = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())})
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def test_projects_shelf_lists_saves_with_route():
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    projects = client.get("/api/projects").json()["projects"]
    ids = [p["project_id"] for p in projects]
    assert pid in ids
    me = next(p for p in projects if p["project_id"] == pid)
    assert me["route"] == "Genocide"
    assert me["love"] == 20


def test_transcript_persists_across_calls(monkeypatch):
    monkeypatch.setattr(
        appmod, "generate_reply",
        lambda sp, um, **k: {"text": "heya, kid.", "model": "m"},
    )
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    # Empty before any chat.
    assert client.get(f"/api/projects/{pid}/conversations/sans").json()["messages"] == []

    client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "hi"})
    msgs = client.get(f"/api/projects/{pid}/conversations/sans").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "hi"
    assert msgs[1]["content"] == "heya, kid."


def test_transcripts_are_per_character(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "ok", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "to sans"})
    client.post(f"/api/projects/{pid}/chat", json={"character": "toriel", "message": "to toriel"})
    sans = client.get(f"/api/projects/{pid}/conversations/sans").json()["messages"]
    toriel = client.get(f"/api/projects/{pid}/conversations/toriel").json()["messages"]
    assert sans[0]["content"] == "to sans"
    assert toriel[0]["content"] == "to toriel"
    assert len(sans) == 2 and len(toriel) == 2
