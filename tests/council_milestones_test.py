"""The Council (whole-cast reaction) + milestones (the self-filling journal)."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from council import build_council
from milestones import detect_milestones

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(route="Neutral", love=5, name="Frisk", dispositions=None):
    return {"play_state": {"name": name, "love": love}, "route": {"route": route, "confidence": "high"},
            "kills": {"total": 5}, "dispositions": dispositions or {}}


# ── The Council ──────────────────────────────────────────────────────────────

def test_council_covers_cast_with_stance_and_line():
    co = build_council(_truth("Genocide"))
    assert len(co) == 9
    assert all(e["line"] and e["stance"] for e in co)
    assert {e["character"] for e in co} >= {"Sans", "Flowey", "Toriel"}
    assert all(e["stance"] == "hostile" for e in co)        # genocide → all turned


def test_council_warm_on_pacifist():
    assert all(e["stance"] == "warm" for e in build_council(_truth("Pacifist")))


def test_council_line_carries_a_loved_ones_fate():
    # Sans cares about Papyrus; on a run where Papyrus was killed his line names it.
    t = _truth("Genocide", dispositions={"Papyrus": {"status": "killed"}})
    sans = next(e for e in build_council(t) if e["character"] == "Sans")
    assert "Papyrus is gone" in sans["line"]


# ── Milestones ───────────────────────────────────────────────────────────────

def _snap(c, love=None, route="Neutral", kills=None):
    return {"counter": c, "love": love, "route": route, "total_kills": kills}


def test_first_steps_only_on_first_reading():
    kinds = {m["kind"] for m in detect_milestones(_truth(), [_snap(1)])}
    assert "first_steps" in kinds
    assert "first_steps" not in {m["kind"] for m in detect_milestones(_truth(), [_snap(1), _snap(2)])}


def test_love_ceiling_and_genocide_and_mercy():
    assert "love_ceiling" in {m["kind"] for m in detect_milestones(_truth("Genocide", love=20), [_snap(1)])}
    assert "genocide_confirmed" in {m["kind"] for m in detect_milestones(_truth("Genocide"), [_snap(1)])}
    assert "true_mercy" in {m["kind"] for m in detect_milestones(_truth("Pacifist", love=1), [_snap(1)])}


def test_reset_and_turn_milestones():
    snaps = [_snap(1, love=20, route="Genocide"), _snap(2, love=1, route="Pacifist")]
    kinds = {m["kind"] for m in detect_milestones(_truth("Pacifist", love=1), snaps)}
    assert "the_reset" in kinds and "path_turned" in kinds


# ── endpoints + auto-fill ────────────────────────────────────────────────────

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


def test_council_endpoint():
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.get(f"/api/projects/{pid}/council").json()
    assert len(r["council"]) == 9 and r["council"][0]["stance"] == "warm"
    assert client.get("/api/projects/999999/council").status_code == 404


def test_journal_autofills_on_upload_and_dedupes():
    pid = _upload("file0_genocide", "undertale_genocide.ini")   # LV20, Genocide
    kinds = [e["kind"] for e in client.get(f"/api/projects/{pid}/journal").json()["entries"]]
    assert {"first_steps", "love_ceiling", "genocide_confirmed"} <= set(kinds)
    n = len(kinds)
    # re-reading the SAME state adds nothing (de-duped by kind)
    _refresh(pid, "file0_genocide", "undertale_genocide.ini")
    assert len(client.get(f"/api/projects/{pid}/journal").json()["entries"]) == n


def test_journal_autofills_reset_on_regressing_refresh():
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    _refresh(pid, "file0_pacifist", "undertale_pacifist.ini")   # LV 20 -> 1 = a reset
    kinds = {e["kind"] for e in client.get(f"/api/projects/{pid}/journal").json()["entries"]}
    assert "the_reset" in kinds and "path_turned" in kinds
