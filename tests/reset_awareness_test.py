"""Reset / timeline detection — the app notices when you loaded an earlier save."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from ledger import detect_resets, build_reset_awareness
from chronicle import build_chronicle

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _snap(counter, love=None, kills=None, route="Neutral"):
    return {"counter": counter, "love": love, "total_kills": kills, "route": route}


def test_no_reset_when_monotonic():
    snaps = [_snap(1, love=1, kills=0), _snap(2, love=5, kills=10), _snap(3, love=12, kills=40)]
    assert detect_resets(snaps) == []


def test_love_regression_is_a_reset():
    snaps = [_snap(1, love=12, kills=40), _snap(2, love=1, kills=0)]
    events = detect_resets(snaps)
    assert any(e["field"] == "LOVE" and e["from"] == 12 and e["to"] == 1 for e in events)


def test_kills_regression_is_a_reset():
    snaps = [_snap(1, love=3, kills=50), _snap(2, love=3, kills=2)]
    assert any(e["field"] == "kills" for e in detect_resets(snaps))


def test_reset_awareness_text():
    snaps = [_snap(1, love=20, kills=80), _snap(2, love=1, kills=0)]
    block = build_reset_awareness(snaps)
    assert "went backward" in block.lower() or "fell from" in block.lower()
    assert "loaded" in block.lower()


def test_reset_awareness_empty_when_none():
    assert build_reset_awareness([_snap(1, love=1), _snap(2, love=2)]) == ""


def test_chronicle_timeline_bends_section():
    truth = {"play_state": {"name": "Frisk", "love": 1}, "route": {"route": "Pacifist"}, "kills": {"total": 0}}
    snaps = [_snap(1, love=20, kills=80, route="Genocide"), _snap(2, love=1, kills=0, route="Pacifist")]
    md = build_chronicle(truth, snaps)["markdown"]
    assert "## The Timeline Bends" in md
    assert "loaded" in md.lower()


# ── app: Sans feels the reset across a refresh that regresses the numbers ─────

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


def test_sans_feels_the_reset(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    # read a Genocide save (LOVE 20), then "load" an earlier Pacifist save (LOVE 1)
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    _refresh(pid, "file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "sans", "message": "feel anything?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "NUMBERS WENT BACKWARD" in sp
    # a character who does NOT feel resets gets no such block
    r2 = client.post(f"/api/projects/{pid}/chat",
                     json={"character": "papyrus", "message": "hi"}).json()
    assert "NUMBERS WENT BACKWARD" not in r2["grounding"]["system_prompt"]
