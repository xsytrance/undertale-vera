"""Cross-save recognition — New Game+: a save-aware character knows you came
before under a different save. SACRED facts (other saves' real fields), FREE voice."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from crossave import build_recognition_grounding, build_echo_grounding, darkest_prior, differs

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


# ── The Other's Echo (pure) ──────────────────────────────────────────────────

def test_echo_fires_on_darker_prior():
    cur = {"name": "FRISK", "route": "Pacifist", "love": 1}
    priors = [{"name": "CHARA", "route": "Genocide", "love": 20, "total_kills": 9}]
    echo = build_echo_grounding(cur, priors, voice="flowey")
    assert "OTHER'S ECHO" in echo
    assert "Genocide" in echo and "LOVE 20" in echo and "9 recorded kills" in echo
    assert "same hand on the keys" in echo
    assert "playing NICE" in echo  # flowey's gleeful frame


def test_no_echo_when_current_is_as_dark():
    # current Genocide, prior Genocide → no echo (nothing gentler to distrust)
    cur = {"route": "Genocide", "love": 20}
    assert build_echo_grounding(cur, [{"route": "Genocide", "love": 19}]) == ""
    # current darker than prior → no echo
    assert build_echo_grounding({"route": "Genocide"}, [{"route": "Pacifist"}]) == ""


def test_no_echo_on_clean_neutral_prior():
    # a Neutral prior with no recorded kills leaves no blood to fear
    assert build_echo_grounding({"route": "Pacifist"}, [{"route": "Neutral", "total_kills": 0}]) == ""
    # but a Neutral prior WITH kills does echo
    assert "ECHO" in build_echo_grounding({"route": "Pacifist"}, [{"route": "Neutral", "total_kills": 3}])


def test_darkest_prior_picks_the_bloodiest():
    priors = [
        {"route": "Pacifist", "love": 1},
        {"route": "Genocide", "love": 20, "total_kills": 9},
        {"route": "Neutral", "love": 5, "total_kills": 2},
    ]
    assert darkest_prior(priors)["route"] == "Genocide"
    assert darkest_prior([{"route": "Pacifist"}]) is None  # no blood, no echo


def test_echo_sans_voice():
    echo = build_echo_grounding({"route": "Pacifist"}, [{"route": "Genocide", "love": 20}], voice="sans")
    assert "keep an eye on them" in echo and "wary" in echo


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
    _upload("file0_pacifist", "undertale_pacifist.ini")
    # current save is Genocide (the darkest) → no Echo can fire, so the plain
    # recognition block is what reaches the prompt.
    g = _upload("file0_genocide", "undertale_genocide.ini")
    sp = client.post(f"/api/projects/{g}/chat",
                     json={"character": "flowey", "message": "do you know me?"}
                     ).json()["grounding"]["system_prompt"]
    assert "I'D FORGET" in sp  # cross-save recognition reached flowey's prompt
    assert "OTHER'S ECHO" not in sp  # nothing darker than this run to echo


def test_recognition_endpoint_reports_echo():
    _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")
    rec = client.get(f"/api/projects/{b}/recognition").json()
    assert rec["echo_present"] is True
    assert rec["darkest"]["route"] == "Genocide"
    assert "OTHER'S ECHO" in rec["echo"]["flowey"]


def test_flowey_chat_echo_supersedes_recognition(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")  # gentler face over a bloody past
    sp = client.post(f"/api/projects/{b}/chat",
                     json={"character": "flowey", "message": "hi"}).json()["grounding"]["system_prompt"]
    assert "OTHER'S ECHO" in sp


def test_meta_off_suppresses_recognition(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    _upload("file0_genocide", "undertale_genocide.ini")
    b = _upload("file0_pacifist", "undertale_pacifist.ini")
    sp = client.post(f"/api/projects/{b}/chat",
                     json={"character": "flowey", "message": "hi", "options": {"meta": "off"}}
                     ).json()["grounding"]["system_prompt"]
    assert "I'D FORGET" not in sp  # the Options 'Save/reset talk: off' dial mutes it
