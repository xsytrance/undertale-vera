"""Cross-save recognition — New Game+: a save-aware character knows you came
before under a different save. SACRED facts (other saves' real fields), FREE voice."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from crossave import build_recognition_grounding, differs

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── pure ─────────────────────────────────────────────────────────────────────

def test_no_priors_is_empty():
    assert build_recognition_grounding({"name": "FRISK", "route": "Pacifist"}, []) == ""
    assert build_recognition_grounding({"name": "FRISK"}, None) == ""


def test_differs_only_on_known_fields():
    assert differs({"name": "FRISK"}, {"name": "CHARA"})
    assert differs({"route": "Pacifist"}, {"route": "Genocide"})
    # unknown on either side is never a difference (no guessing)
    assert not differs({"name": None}, {"name": "CHARA"})
    assert not differs({"route": "Genocide"}, {"route": None})
    assert not differs({"name": "FRISK"}, {"name": "FRISK"})


def test_recognition_surfaces_a_different_prior():
    cur = {"name": "FRISK", "route": "Pacifist", "love": 1}
    priors = [{"name": "CHARA", "route": "Genocide", "love": 19}]
    block = build_recognition_grounding(cur, priors, voice="flowey")
    assert "CHARA" in block and "Genocide" in block and "LOVE 19" in block
    assert "different face" in block
    assert "I'D FORGET" in block  # flowey frame


def test_recognition_honours_unknown_fields():
    block = build_recognition_grounding({"name": "FRISK"}, [{"name": None, "route": None, "love": None}])
    assert "no name I could read" in block
    assert "LOVE" not in block  # love unknown → never stated

def test_recognition_caps_and_voices():
    cur = {"name": "FRISK", "route": "Pacifist"}
    priors = [{"name": f"RUN{i}", "route": "Genocide"} for i in range(5)]
    sans = build_recognition_grounding(cur, priors, voice="sans", limit=2)
    assert sans.count("\n  - ") == 2  # capped
    assert "you've shown me other saves" in sans  # sans frame


# ── endpoint wiring ──────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_recognition_endpoint_sees_a_sibling_save():
    a = _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")
    rec = client.get(f"/api/projects/{b}/recognition").json()
    assert rec["present"] is True
    assert rec["count"] >= 1
    # the genocide sibling 'a' must be recognised from pacifist save 'b'
    assert "Genocide" in rec["flowey"]
    assert any(p.get("route") == "Genocide" for p in rec["priors"])


def test_flowey_chat_recognises_a_prior_save(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")
    sp = client.post(f"/api/projects/{b}/chat",
                     json={"character": "flowey", "message": "do you know me?"}
                     ).json()["grounding"]["system_prompt"]
    assert "I'D FORGET" in sp  # cross-save recognition reached flowey's prompt


def test_meta_off_suppresses_recognition(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")
    sp = client.post(f"/api/projects/{b}/chat",
                     json={"character": "flowey", "message": "hi", "options": {"meta": "off"}}
                     ).json()["grounding"]["system_prompt"]
    assert "I'D FORGET" not in sp  # the Options 'Save/reset talk: off' dial mutes it
