"""The Chronicle — a save's whole story, narrated from parser-truth alone."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from chronicle import build_chronicle

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(**over):
    t = {
        "play_state": {"name": "Frisk", "love": 1, "play_time_frames": 108000,
                       "room_name": "ruins_entrance", "fun": 66, "toriel_pie": 2},
        "route": {"route": "Pacifist", "confidence": "high"},
        "kills": {"total": 0},
        "dispositions": {
            "Toriel": {"character": "Toriel", "status": "spared", "flags": ["ts"]},
            "Papyrus": {"character": "Papyrus", "status": "befriended", "flags": ["pd"]},
            "Undyne": {"character": "Undyne", "status": "unknown", "flags": []},
        },
    }
    t.update(over)
    return t


def test_chronicle_has_title_and_sections():
    c = build_chronicle(_truth())
    md = c["markdown"]
    assert c["title"] == "The Chronicle of Frisk"
    assert "# The Chronicle of Frisk" in md
    for section in ("## The Path", "## The Record", "## Those You Met", "## The Verdict"):
        assert section in md


def test_sacred_facts_render():
    md = build_chronicle(_truth())["markdown"]
    assert "**Pacifist** route (confidence: high)" in md
    assert "LOVE (LV): 1" in md
    assert "Recorded kills: 0" in md
    assert "Furthest known place: the Ruins" in md      # from room_name
    assert "about 1 hour" in md                          # 108000 frames @30fps
    assert "The pie Toriel baked: cinnamon" in md        # toriel_pie=2


def test_dispositions_only_definite():
    md = build_chronicle(_truth())["markdown"]
    assert "Toriel — spared" in md
    assert "Papyrus — befriended" in md
    assert "Undyne" not in md          # unknown status is not asserted


def test_fun_anomaly_section():
    md = build_chronicle(_truth())["markdown"]
    assert "## An Anomaly" in md
    assert "Fun value reads 66" in md


def test_no_anomaly_section_for_common_fun():
    t = _truth()
    t["play_state"]["fun"] = 88        # a no-event value
    assert "## An Anomaly" not in build_chronicle(t)["markdown"]


def test_unknowns_left_unwritten_not_guessed():
    t = {
        "play_state": {"name": None, "love": None},
        "route": {"route": "undetermined", "confidence": "unknown"},
        "kills": {"total": None},
    }
    c = build_chronicle(t)
    md = c["markdown"]
    assert c["title"] == "The Chronicle of an Unnamed Fallen Human"
    assert "LOVE (LV): not recorded" in md
    assert "Recorded kills: not recorded" in md
    assert "no route is claimed" in md.lower()
    assert "## Those You Met" not in md        # nothing definite → section omitted
    assert "## An Anomaly" not in md


def test_remembrance_section_across_visits():
    snaps = [
        {"counter": 1, "route": "Pacifist"},
        {"counter": 2, "route": "Genocide"},
    ]
    md = build_chronicle(_truth(), snaps)["markdown"]
    assert "## What the Save Remembers" in md
    assert "read 2 times" in md
    assert "path turned from Pacifist to Genocide" in md


def test_single_visit_omits_remembrance():
    md = build_chronicle(_truth(), [{"counter": 1, "route": "Pacifist"}])["markdown"]
    assert "## What the Save Remembers" not in md


# ── app endpoint ─────────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_chronicle_endpoint():
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.get(f"/api/projects/{pid}/chronicle").json()
    assert r["project_id"] == pid
    assert r["route"] == "Pacifist"
    assert "# The Chronicle of" in r["markdown"]
    assert "## The Verdict" in r["markdown"]


def test_chronicle_endpoint_404():
    assert client.get("/api/projects/999999/chronicle").status_code == 404
