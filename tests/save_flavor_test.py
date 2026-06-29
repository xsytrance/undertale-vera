"""Save texture + the Fun-value anomaly — deep-cut SACRED grounding."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from save_flavor import (
    area_from_save, pie_flavor, humanize_playtime, fun_value_event,
    build_texture_grounding, build_anomaly_grounding,
)

client = TestClient(appmod.app)


# ── area (from room name only — never from fragile room numbers) ─────────────

def test_area_from_room_name():
    assert area_from_save({"play_state": {"room_name": "ruins_entrance"}}) == "the Ruins"
    assert area_from_save({"play_state": {"room_name": "core_final"}}) == "the CORE"
    assert area_from_save({"play_state": {"room_name": "water_dump"}}) == "Waterfall"


def test_area_none_when_no_room_name():
    assert area_from_save({"play_state": {"room": 145}}) is None
    assert area_from_save({}) is None


# ── pie / playtime ───────────────────────────────────────────────────────────

def test_pie_flavor():
    assert pie_flavor({"play_state": {"toriel_pie": 1}}) == "butterscotch"
    assert pie_flavor({"play_state": {"toriel_pie": 2}}) == "cinnamon"
    assert pie_flavor({"play_state": {}}) is None


def test_humanize_playtime():
    assert humanize_playtime(9504) == "about 5 minutes"     # corpus low end
    assert humanize_playtime(108000) == "about 1 hour"      # 60 min
    assert humanize_playtime(None) is None
    assert humanize_playtime(0) is None


# ── the Fun value (documented thresholds) ────────────────────────────────────

def test_fun_value_events():
    assert fun_value_event(13)["name"] == "the Wrong Number Song"   # corpus genocide run
    assert fun_value_event(62)["tier"] == "gaster"
    assert fun_value_event(66)["name"].startswith("the gray door")
    assert fun_value_event(90)["name"] == "the Goner Kid"


def test_fun_value_common_values_have_no_event():
    # Most runs have no event — 88 (corpus pacifist), 44, 64 are silent.
    assert fun_value_event(88) is None
    assert fun_value_event(44) is None
    assert fun_value_event(64) is None
    assert fun_value_event(None) is None


def test_anomaly_grounding_only_for_an_event():
    assert build_anomaly_grounding({"play_state": {"fun": 88}}) == ""
    g = build_anomaly_grounding({"play_state": {"fun": 66}})
    assert "Fun value is 66" in g
    assert "deepest secrets" in g                # gaster-tier framing
    quirk = build_anomaly_grounding({"play_state": {"fun": 13}})
    assert "Wrong Number Song" in quirk
    assert "deepest secrets" not in quirk        # quirk tier stays light


def test_texture_grounding_assembles_known_bits():
    g = build_texture_grounding({"play_state": {
        "room_name": "snowdin_town", "play_time_frames": 108000, "toriel_pie": 2}})
    assert "Snowdin" in g and "about 1 hour" in g and "cinnamon" in g


def test_texture_grounding_empty_when_nothing_known():
    assert build_texture_grounding({"play_state": {}}) == ""


# ── app wiring: anomaly gated to meta-aware characters ───────────────────────

def _file0(love=66):
    lines = [""] * 548
    lines[0], lines[1], lines[2], lines[35] = "Frisk", "1", "20", "66"
    return "\n".join(lines).encode()


def _upload_fun66():
    ini = '[General]\nName="Frisk"\nLove="1"\nKills="0"\nFun="66"\nRoomName="water_crystal"\n[Toriel]\nBscotch="2.000000"\n'
    return client.post("/api/upload", files={
        "file0": ("file0", _file0()), "undertale_ini": ("undertale.ini", ini.encode()),
    }).json()["project_id"]


def test_sans_gets_the_anomaly_block(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload_fun66()
    r = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "ANOMALY IN THE CODE" in sp
    assert "Fun value is 66" in sp
    # texture reaches everyone
    assert "Waterfall" in sp
    assert r["provenance"]["sacred"]["fun_event"].startswith("the gray door")


def test_non_meta_character_does_not_get_the_anomaly(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload_fun66()
    r = client.post(f"/api/projects/{pid}/chat", json={"character": "papyrus", "message": "?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "ANOMALY IN THE CODE" not in sp      # gated away from Papyrus
    assert "Waterfall" in sp                     # but he still gets texture
