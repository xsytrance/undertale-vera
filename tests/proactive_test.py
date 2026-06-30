"""Proactive contact — the characters message you first."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from llm_client import LLMUnavailable
import proactive


client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(route="Neutral", dispositions=None):
    return {"play_state": {"name": "Frisk", "love": 5}, "route": {"route": route, "confidence": "medium"},
            "kills": {"total": 5}, "dispositions": dispositions or {}}


# ── pure ─────────────────────────────────────────────────────────────────────

def test_pick_reacher_prefers_the_most_at_stake():
    # Sans grieves Papyrus's death → highest urgency, so he reaches out.
    t = _truth(route="Neutral", dispositions={"Papyrus": {"status": "killed"}})
    pick = proactive.pick_reacher(t)
    assert pick["character"] == "Sans" and pick["stance"] == "grieving"


def test_pick_reacher_on_pacifist_is_warm():
    assert proactive.pick_reacher(_truth(route="Pacifist"))["stance"] == "warm"


def test_reach_out_instruction_and_fallback():
    assert "Pacifist" in proactive.reach_out_instruction(_truth("Pacifist"))
    f = proactive.fallback_reach_out("Sans", _truth("Genocide"))
    assert "Sans" in f and "Genocide" in f


# ── endpoint ─────────────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_reach_out_picks_and_persists(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "heya. you've been quiet. just checking in.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/reach-out", json={}).json()
    assert r["character"] in {"Sans", "Toriel", "Papyrus", "Flowey", "Undyne",
                              "Alphys", "Asgore", "Mettaton", "Napstablook"}
    assert "checking in" in r["message"]
    # the unprompted message is persisted to that character's transcript
    convo = client.get(f"/api/projects/{pid}/conversations/{r['character'].lower()}").json()
    assert any(m.get("unprompted") and m["role"] == "assistant" for m in convo["messages"])


def test_reach_out_specific_character_and_fallback(monkeypatch):
    def boom(*a, **k):
        raise LLMUnavailable("no model")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/reach-out", json={"character": "flowey"}).json()
    assert r["character"] == "Flowey"
    assert r["message"]                       # deterministic fallback, never empty
    assert "Genocide" in r["message"]


def test_reach_out_unknown_character_404(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "x", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    assert client.post(f"/api/projects/{pid}/reach-out", json={"character": "nobody"}).status_code == 404


def test_reach_out_404_project():
    assert client.post("/api/projects/999999/reach-out", json={}).status_code == 404
