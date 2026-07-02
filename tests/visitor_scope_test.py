"""Public-deployment hardening: visitor scoping, the guided gate, upload caps."""
import os

import pytest
from fastapi.testclient import TestClient

import undertale_vera_app as appmod


FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), "rb") as f:
        return f.read()


@pytest.fixture
def scoped(monkeypatch):
    monkeypatch.setattr(appmod, "VISITOR_SCOPE", True)
    yield


def _upload(client):
    r = client.post("/api/upload", files={"file0": ("file0", _read("file0_pacifist"))})
    assert r.status_code == 200
    return r.json()["project_id"]


def test_visitors_cannot_see_each_other(scoped):
    alice = TestClient(appmod.app)
    bob = TestClient(appmod.app)
    pid = _upload(alice)
    assert "ember_visitor" in alice.cookies
    # Alice sees her save; Bob's shelf doesn't include it
    mine = [p["project_id"] for p in alice.get("/api/projects").json()["projects"]]
    theirs = [p["project_id"] for p in bob.get("/api/projects").json()["projects"]]
    assert pid in mine and pid not in theirs
    # direct object reference is refused too
    assert bob.get(f"/api/projects/{pid}/save-truth").status_code == 404
    assert alice.get(f"/api/projects/{pid}/save-truth").status_code == 200
    # ...and so is chatting with someone else's save
    r = bob.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "hi"})
    assert r.status_code == 404


def test_pre_scoping_saves_stay_visible(scoped):
    """Projects with visitor=NULL (the single-user era) are not orphaned."""
    legacy = TestClient(appmod.app)
    db = appmod.SessionLocal()
    try:
        row = appmod.Project(name="legacy", save_data={"play_state": {}}, visitor=None)
        db.add(row); db.commit(); db.refresh(row)
        pid = row.id
    finally:
        db.close()
    assert legacy.get(f"/api/projects/{pid}/save-truth").status_code == 200


def test_shelf_cap(scoped, monkeypatch):
    monkeypatch.setattr(appmod, "MAX_PROJECTS_PER_VISITOR", 2)
    c = TestClient(appmod.app)
    _upload(c); _upload(c)
    r = c.post("/api/upload", files={"file0": ("file0", _read("file0_pacifist"))})
    assert r.status_code == 429


def test_upload_size_cap(monkeypatch):
    monkeypatch.setattr(appmod, "MAX_SAVE_BYTES", 100)
    c = TestClient(appmod.app)
    r = c.post("/api/upload", files={"file0": ("file0", b"x" * 200)})
    assert r.status_code == 413


def test_guided_watch_forbidden_on_lite(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBER_EDITION", "lite")
    c = TestClient(appmod.app)
    assert c.post("/api/guided/watch", json={"path": str(tmp_path)}).status_code == 403
    assert c.request("DELETE", "/api/guided/watch", json={"path": "/x"}).status_code == 403
    monkeypatch.delenv("EMBER_EDITION")
    # pro stays functional
    assert c.post("/api/guided/watch", json={"path": str(tmp_path)}).status_code == 200
    c.request("DELETE", "/api/guided/watch", json={"path": str(tmp_path)})


def test_scope_off_means_no_change():
    """Default installs: no cookie, everything visible — exactly as before."""
    c = TestClient(appmod.app)
    r = c.get("/api/projects")
    assert r.status_code == 200
    assert "ember_visitor" not in r.cookies
