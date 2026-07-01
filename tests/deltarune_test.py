"""Deltarune Chapter 1 foundation — parser-truth, honest truth, game-aware upload."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import deltarune_parser as dp
from deltarune_truth import build_deltarune_truth


client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), "rb") as f:
        return f.read()


# ── parser (pure) ────────────────────────────────────────────────────────────

def test_filename_detection():
    assert dp.looks_like_deltarune("filech1_0")
    assert dp.looks_like_deltarune("filech2_3")
    assert not dp.looks_like_deltarune("file0")
    assert not dp.looks_like_deltarune("undertale.ini")
    assert dp.chapter_slot_from_filename("filech1_2") == (1, 2)


def test_parse_names_only_documented_fields():
    p = dp.parse_deltarune_save(_read("filech1_0"), "filech1_0")
    assert p["game"] == "deltarune" and p["chapter"] == 1 and p["slot"] == 0
    assert p["fields"]["name"] == "Kris" and p["confidence"]["name"] == "medium"
    assert p["fields"]["dark_dollars"] == 1997 and p["confidence"]["dark_dollars"] == "medium"
    # undocumented lines stay raw, never interpreted
    assert p["raw_lines"][3] == "2" and p["raw_lines"][15] == "Wood Blade"
    assert "party" not in p["fields"]


def test_parse_never_crashes_on_garbage():
    p = dp.parse_deltarune_save(b"\xff\xfe weird\nstuff", "filech1_1")
    assert p["fields"]["dark_dollars"] is None and p["confidence"]["dark_dollars"] == "unknown"
    assert p["warnings"]   # short save → honest warnings


# ── truth (pure): honest, SaveTruth-compatible ───────────────────────────────

def test_truth_shape_and_honesty():
    t = build_deltarune_truth(dp.parse_deltarune_save(_read("filech1_0"), "filech1_0"))
    assert t["game"] == "deltarune" and t["chapter"] == 1
    assert t["play_state"]["name"] == "Kris"
    assert t["play_state"]["gold"] == 1997          # dark dollars ride the gold seat
    assert t["play_state"]["love"] is None          # no LOVE asserted from lore
    assert t["kills"]["total"] is None
    # route honesty: Ch1 Pacifist/Violent isn't corroborated from flags yet
    assert t["route"]["route"] == "undetermined" and t["route"]["confidence"] == "unknown"


# ── upload (game-aware) ──────────────────────────────────────────────────────

def test_upload_filech1_creates_deltarune_project():
    r = client.post("/api/upload", files={"file0": ("filech1_0", _read("filech1_0"))}).json()
    assert r["save_truth"]["game"] == "deltarune"
    assert r["save_truth"]["play_state"]["name"] == "Kris"
    pid = r["project_id"]
    listing = client.get("/api/projects").json()["projects"]
    mine = next(p for p in listing if p["project_id"] == pid)
    assert mine["game"] == "deltarune" and mine["chapter"] == 1
    assert mine["route"] == "undetermined"


def test_upload_file0_still_undertale():
    with open(os.path.join(FIX, "file0_pacifist"), "rb") as f0, \
         open(os.path.join(FIX, "undertale_pacifist.ini"), "rb") as ini:
        r = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", ini.read())
        }).json()
    listing = client.get("/api/projects").json()["projects"]
    mine = next(p for p in listing if p["project_id"] == r["project_id"])
    assert mine["game"] == "undertale"


def test_deltarune_chat_stays_grounded(monkeypatch):
    """A Deltarune save flows through the same wall: route undetermined → told so."""
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "ok", "model": "m"})
    pid = client.post("/api/upload", files={"file0": ("filech1_0", _read("filech1_0"))}).json()["project_id"]
    client.post(f"/api/projects/{pid}/chat",
                json={"character": "toriel", "message": "hi", "history": []})
    assert "undetermined" in seen["prompt"].lower() or "not yet" in seen["prompt"].lower()
    assert "Kris" in seen["prompt"]   # the sacred name rides the same wall
