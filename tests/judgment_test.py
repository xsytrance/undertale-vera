"""The Judgment beat: sacred facts read back; unknowns named; nothing invented."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from judgment import build_judgment, classify_verdict

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(name, love, route, kills):
    return {
        "play_state": {"name": name, "love": love},
        "route": {"route": route, "confidence": "high", "reasons": []},
        "kills": {"total": kills},
    }


# ── pure ─────────────────────────────────────────────────────────────────────

def test_verdict_tracks_route():
    assert classify_verdict("Genocide")["label"] == "the dust on your hands"
    assert classify_verdict("Pacifist")["label"] == "clean hands"
    assert classify_verdict(None)["label"] == "the verdict's still open"


def test_facts_are_verbatim_from_savetruth():
    j = build_judgment(_truth("Chara", 20, "Genocide", 9))
    assert j["facts"] == {
        "name": "Chara", "love": 20, "route": "Genocide",
        "route_confidence": "high", "total_kills": 9,
    }
    assert j["honest_gaps"] == []   # everything known


def test_unknowns_are_named_not_guessed():
    j = build_judgment(_truth(None, None, "undetermined", None))
    gaps = " ".join(j["honest_gaps"])
    assert "LOVE could not be read" in gaps
    assert "kill count could not be read" in gaps
    assert "route is undetermined" in gaps
    assert j["verdict"]["label"] == "the verdict's still open"


# ── app ──────────────────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        r = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())})
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def test_structured_judgment_endpoint():
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    j = client.get(f"/api/projects/{pid}/judgment").json()["judgment"]
    assert j["facts"]["route"] == "Genocide"
    assert j["facts"]["love"] == 20
    assert j["verdict"]["label"] == "the dust on your hands"


def test_spoken_judgment_is_grounded(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        appmod, "generate_reply",
        lambda sp, um, **k: (captured.__setitem__("sp", sp), captured.__setitem__("um", um),
                             {"text": "heya. let's review.", "model": "m"})[2],
    )
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/judgment/speak", json={"character": "sans"}).json()
    assert r["spoken"] == "heya. let's review."
    assert "Genocide" in captured["sp"]              # sacred route in the prompt
    assert "judgment" in captured["um"].lower()       # judgment-framed ask
    assert r["judgment"]["facts"]["love"] == 20


def test_spoken_judgment_degrades_gracefully(monkeypatch):
    from llm_client import LLMUnavailable

    def boom(*a, **k):
        raise LLMUnavailable("no model")

    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/judgment/speak", json={"character": "sans"}).json()
    assert r["grounding"]["source"] == "deterministic_fallback"
    # Falls back to the deterministic Pacifist verdict line — still honest.
    assert "spared every soul" in r["spoken"]
