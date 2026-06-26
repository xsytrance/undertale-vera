"""The remembrance ledger ('the save remembers') — Bucket A, additive, honest."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from ledger import build_remembrance_grounding, summarize_change

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── pure function tests ──────────────────────────────────────────────────────

def test_summarize_change_derives_real_deltas():
    prev = {"name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0}
    curr = {"name": "Frisk", "love": 20, "route": "Genocide", "total_kills": 9}
    out = summarize_change(prev, curr)
    assert any("LOVE has risen from 1 to 20" in s for s in out)
    assert any("path turned from Pacifist to Genocide" in s for s in out)
    assert any("kills went from 0 to 9" in s for s in out)


def test_summarize_change_claims_nothing_when_unknown_or_equal():
    assert summarize_change({"love": None}, {"love": 5}) == []      # unknown → no claim
    assert summarize_change({"love": 5}, {"love": 5}) == []          # equal → no claim


def test_remembrance_empty_below_two_visits():
    assert build_remembrance_grounding([]) == ""
    assert build_remembrance_grounding([{"love": 1}]) == ""


def test_remembrance_renders_visit_and_deltas():
    snaps = [
        {"name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0},
        {"name": "Frisk", "love": 20, "route": "Genocide", "total_kills": 9},
    ]
    block = build_remembrance_grounding(snaps)
    assert "visit #2" in block
    assert "Pacifist to Genocide" in block
    assert "never invented" in block


# ── app-level: additive ledger across visits ────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        r = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())})
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def _refresh(pid, stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        r = client.post(f"/api/projects/{pid}/refresh-save", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())})
    assert r.status_code == 200, r.text
    return r.json()


def test_ledger_is_additive_and_remembers_the_turn():
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    mem1 = client.get(f"/api/projects/{pid}/save-memory").json()
    assert len(mem1["snapshots"]) == 1
    assert mem1["remembrance"] == ""             # nothing to remember on visit 1

    # A later, darker visit.
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    mem2 = client.get(f"/api/projects/{pid}/save-memory").json()
    assert len(mem2["snapshots"]) == 2           # additive — prior row kept
    assert mem2["snapshots"][0]["route"] == "Pacifist"   # first visit untouched
    assert mem2["snapshots"][1]["route"] == "Genocide"
    assert "Pacifist to Genocide" in mem2["remembrance"]


def test_chat_grounding_includes_remembrance(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        appmod, "generate_reply",
        lambda sp, um, **k: (captured.__setitem__("sp", sp), {"text": "i remember.", "model": "m"})[1],
    )
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "hey"})
    assert r.status_code == 200
    assert "WHAT THE SAVE REMEMBERS" in captured["sp"]
    assert "Pacifist to Genocide" in captured["sp"]


def test_memory_write_does_not_add_a_snapshot():
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    before = len(client.get(f"/api/projects/{pid}/save-memory").json()["snapshots"])
    client.post(f"/api/projects/{pid}/memory/sans/remember", json={"text": "hi"})
    after = len(client.get(f"/api/projects/{pid}/save-memory").json()["snapshots"])
    assert before == after == 1   # Bucket B never writes the Bucket A ledger
