"""Sans the save-aware judge — the 'path turned' event (SACRED ledger history).

Sans is canonically aware of saves, loads, and resets. When the ledger holds
two or more readings, HE (and only he) gets a SACRED awareness block surfacing
the parser-confirmed visit count and any route turn. The numbers are real; the
'he notices' is his character. Pure-helper tests first, then the wired app path.
"""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from ledger import detect_route_turn, build_sans_awareness, build_flowey_awareness

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _snap(counter, route, love=None, kills=None, name="Frisk"):
    return {
        "counter": counter,
        "name": name,
        "love": love,
        "route": route,
        "route_confidence": "medium",
        "total_kills": kills,
    }


# ── detect_route_turn (pure) ─────────────────────────────────────────────────

def test_route_turn_none_on_single_snapshot():
    assert detect_route_turn([_snap(1, "Pacifist")]) is None


def test_route_turn_none_when_stable():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Pacifist"), _snap(3, "Pacifist")]
    assert detect_route_turn(snaps) is None


def test_route_turn_detected():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Genocide")]
    turn = detect_route_turn(snaps)
    assert turn == {"from": "Pacifist", "to": "Genocide", "visit": 2}


def test_route_turn_returns_latest_change():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Neutral"), _snap(3, "Genocide")]
    turn = detect_route_turn(snaps)
    assert turn["from"] == "Neutral" and turn["to"] == "Genocide" and turn["visit"] == 3


def test_route_turn_ignores_unknown_route():
    # A None route on either side is not a "turn" — never invented.
    snaps = [_snap(1, None), _snap(2, "Pacifist")]
    assert detect_route_turn(snaps) is None


# ── build_sans_awareness (pure) ──────────────────────────────────────────────

def test_sans_awareness_empty_on_single_visit():
    assert build_sans_awareness([_snap(1, "Pacifist")]) == ""


def test_sans_awareness_reports_visit_count_and_turn():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Genocide")]
    block = build_sans_awareness(snaps)
    assert "read 2 times" in block
    assert "from Pacifist to Genocide" in block


def test_sans_awareness_without_turn_still_counts_visits():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Pacifist")]
    block = build_sans_awareness(snaps)
    assert "read 2 times" in block
    assert "the path turned" not in block


# ── app: Sans gets the block, others don't; path_turn rides the responses ─────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def _refresh(pid, stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post(f"/api/projects/{pid}/refresh-save", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()


def test_refresh_surfaces_path_turn():
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    assert r["path_turn"] is not None
    assert r["path_turn"]["to"] == "Genocide"


def test_sans_chat_includes_awareness_block(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "heya. been here before, huh.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "sans", "message": "do you know me?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "read 2 times" in sp
    assert "from Pacifist to Genocide" in sp
    assert r["path_turn"] is not None and r["path_turn"]["to"] == "Genocide"


def test_flowey_awareness_empty_on_single_visit():
    assert build_flowey_awareness([_snap(1, "Pacifist")]) == ""


def test_flowey_awareness_reports_resets_and_turn():
    snaps = [_snap(1, "Pacifist"), _snap(2, "Genocide")]
    block = build_flowey_awareness(snaps)
    assert "read 2 times" in block
    assert "from Pacifist to Genocide" in block
    assert "never forget" in block          # Flowey's distinct framing


def test_flowey_chat_includes_reset_awareness(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "howdy. again.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "flowey", "message": "do you remember me?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "ACROSS RESETS" in sp
    assert "from Pacifist to Genocide" in sp
    # Sans's variant must NOT also be present — each gets only their own framing.
    assert "you, Sans, notice these things" not in sp


def test_non_sans_chat_omits_awareness_block(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "toriel", "message": "do you know me?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "you, Sans, notice these things" not in sp
    # path_turn still rides every chat response (UI overlay), regardless of speaker.
    assert r["path_turn"] is not None
