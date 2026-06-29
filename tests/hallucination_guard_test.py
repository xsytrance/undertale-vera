"""The hallucination guard + provenance — the wall checked on the actual reply."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from hallucination_guard import check_response
from provenance import build_provenance

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(name="Frisk", love=1, route="Pacifist", kills=0):
    return {
        "play_state": {"name": name, "love": love},
        "route": {"route": route, "confidence": "medium"},
        "kills": {"total": kills},
    }


# ── guard detection (conservative, no false positives) ───────────────────────

def test_clean_reply_passes():
    g = check_response("howdy! nice to see you keeping your hands clean.", _truth())
    assert g["clean"] is True and g["issues"] == []


def test_route_contradiction_flagged():
    # Save is Pacifist; reply asserts a Genocide run.
    g = check_response("you killed everyone down here. there's nothing left but dust.",
                       _truth(route="Pacifist"))
    assert g["clean"] is False
    assert any(i["type"] == "route" for i in g["issues"])


def test_love_contradiction_flagged():
    g = check_response("your LOVE is 19 — that's a lot of power.", _truth(love=1))
    assert any(i["type"] == "love" and i["sacred"] == 1 for i in g["issues"])


def test_kills_contradiction_flagged():
    g = check_response("you killed 50 monsters to get here.", _truth(kills=0))
    assert any(i["type"] == "kills" for i in g["issues"])


def test_matching_facts_do_not_flag():
    # The reply states the TRUE numbers — no contradiction.
    g = check_response("your LOVE is 1 and you killed 0 monsters.", _truth(love=1, kills=0))
    assert g["clean"] is True


def test_route_assertion_on_undetermined_is_flagged():
    g = check_response("you spared everyone — a true pacifist.", _truth(route="undetermined"))
    assert g["clean"] is False


# ── provenance shape ─────────────────────────────────────────────────────────

def test_provenance_separates_sacred_and_free():
    p = build_provenance(_truth(route="Genocide", love=20, kills=9),
                         character="Sans",
                         lore_docs=[{"title": "Waterfall"}],
                         memory_used=True, remembrance_used=False,
                         guard={"clean": True, "issues": []})
    assert p["sacred"]["route"] == "Genocide" and p["sacred"]["love"] == 20
    assert p["free"]["voice"] == "Sans" and "Waterfall" in p["free"]["lore"]
    assert p["free"]["memory_used"] is True


# ── app: chat response carries guard + provenance ────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_chat_includes_guard_and_provenance(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "heya. clean hands, huh.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "who am I?"}).json()
    assert r["guard"]["clean"] is True
    assert r["provenance"]["sacred"]["route"] == "Pacifist"
    assert r["provenance"]["free"]["voice"] == "Sans"


def test_chat_guard_flags_a_contradicting_model(monkeypatch):
    # A misbehaving model claims Genocide on a Pacifist save — the guard catches it.
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "you killed everyone, kid.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "?"}).json()
    assert r["guard"]["clean"] is False
    assert any(i["type"] == "route" for i in r["guard"]["issues"])
