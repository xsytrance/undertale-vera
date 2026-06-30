"""The Keepsake Journal — the book the characters fill, that you carry between worlds."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from llm_client import LLMUnavailable
from journal import inscription_instruction, fallback_inscription, build_journal_markdown

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(route="Pacifist", name="Frisk"):
    return {"play_state": {"name": name, "love": 1}, "route": {"route": route, "confidence": "high"},
            "kills": {"total": 0}}


# ── pure helpers ─────────────────────────────────────────────────────────────

def test_instruction_mentions_route():
    assert "Pacifist" in inscription_instruction(_truth("Pacifist"))
    assert "not yet clear" in inscription_instruction(_truth("undetermined"))


def test_fallback_is_grounded_and_honest():
    f = fallback_inscription("Sans", _truth("Genocide", name="Chara"))
    assert "Chara" in f and "Genocide" in f
    assert "cannot yet say" in fallback_inscription("Sans", _truth("undetermined"))


def test_markdown_export_shape():
    md = build_journal_markdown([
        {"author": "Sans", "text": "heya.", "route_context": "Pacifist"},
    ], project_name="Frisk")
    assert "# The Keepsake Journal — Frisk" in md
    assert "### Sans" in md and "heya." in md
    assert "No one has written" in build_journal_markdown([])


# ── app endpoints ────────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_inscribe_with_model(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "heya kid. you kept it clean. proud of ya.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/journal/inscribe", json={"character": "sans"}).json()
    assert r["entry"]["author"] == "Sans"
    assert "proud of ya" in r["entry"]["text"]
    assert r["entry"]["route_context"] == "Pacifist"
    assert "clean" in r["guard"] and r["guard"]["clean"] is True


def test_inscribe_falls_back_without_model(monkeypatch):
    def boom(*a, **k):
        raise LLMUnavailable("no model")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/journal/inscribe", json={"character": "flowey"}).json()
    assert r["entry"]["author"] == "Flowey"
    assert r["entry"]["text"]                       # a deterministic entry, never empty
    assert "Genocide" in r["entry"]["text"]


def test_journal_is_add_only_and_chronological(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "an entry.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    client.post(f"/api/projects/{pid}/journal/inscribe", json={"character": "sans"})
    client.post(f"/api/projects/{pid}/journal/inscribe", json={"character": "toriel"})
    j = client.get(f"/api/projects/{pid}/journal").json()
    assert [e["counter"] for e in j["entries"]] == [1, 2]          # append-only, ordered
    assert [e["author"] for e in j["entries"]] == ["Sans", "Toriel"]
    assert "# The Keepsake Journal" in j["markdown"]


def test_inscribe_unknown_character_404(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "x", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    assert client.post(f"/api/projects/{pid}/journal/inscribe", json={"character": "nobody"}).status_code == 404


def test_journal_404():
    assert client.get("/api/projects/999999/journal").status_code == 404
