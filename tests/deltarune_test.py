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


# ── the Chapter 1 cast (game-aware registry) ─────────────────────────────────

def test_deltarune_roster_composition():
    from character_config import list_characters
    dr = list_characters("deltarune")
    names = {c["name"] for c in dr}
    # 8 Darkners/Lightners + 4 returning Hometown faces
    assert {"Susie", "Ralsei", "Lancer", "Noelle", "King", "Rouxls Kaard", "Jevil", "Seam"} <= names
    assert {"Toriel", "Asgore", "Alphys", "Sans"} <= names
    assert len(dr) == 12
    # Darkners never leak into the Undertale roster (back-compat default too)
    ut = {c["name"] for c in list_characters()}
    assert "Susie" not in ut and "Jevil" not in ut and "Sans" in ut


def test_hometown_persona_overlay():
    from character_config import get_character
    dr_toriel = get_character("toriel", game="deltarune")
    assert "schoolteacher" in dr_toriel["tone"]
    assert any("school" in s for s in dr_toriel["speaks_of"])
    assert "deltarune" not in dr_toriel          # overlay applied, block consumed
    ut_toriel = get_character("toriel", game="undertale")
    assert "motherly" in ut_toriel["tone"] and "schoolteacher" not in ut_toriel["tone"]
    assert get_character("susie", game="undertale") is None   # no Darkners in Undertale


def test_characters_endpoint_game_param():
    names = {c["name"] for c in client.get("/api/characters", params={"game": "deltarune"}).json()["characters"]}
    assert "Susie" in names and "Jevil" in names and "Papyrus" not in names
    default = {c["name"] for c in client.get("/api/characters").json()["characters"]}
    assert "Susie" not in default and "Papyrus" in default


def test_deltarune_save_gets_deltarune_council_and_affinities():
    pid = client.post("/api/upload", files={"file0": ("filech1_0", _read("filech1_0"))}).json()["project_id"]
    council = client.get(f"/api/projects/{pid}/council").json()["council"]
    names = {v["character"] for v in council}
    assert "Susie" in names and "Ralsei" in names and "Papyrus" not in names
    aff = client.get(f"/api/projects/{pid}/affinities").json()["affinities"]
    assert "Jevil" in aff and "Mettaton" not in aff


def test_deltarune_chat_uses_hometown_persona(monkeypatch):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "ok", "model": "m"})
    pid = client.post("/api/upload", files={"file0": ("filech1_0", _read("filech1_0"))}).json()["project_id"]
    client.post(f"/api/projects/{pid}/chat", json={"character": "toriel", "message": "hi", "history": []})
    assert "schoolteacher" in seen["prompt"]          # Hometown Toriel, not Ruins Toriel
    client.post(f"/api/projects/{pid}/chat", json={"character": "susie", "message": "hi", "history": []})
    assert "bark" in seen["prompt"]                    # Susie's own voice


# ── Across Two Worlds (Phase 4) ──────────────────────────────────────────────

def _tw_setup():
    """One save from each world → the two-worlds beat can fire."""
    with open(os.path.join(FIX, "file0_pacifist"), "rb") as f0, \
         open(os.path.join(FIX, "undertale_pacifist.ini"), "rb") as ini:
        ut = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", ini.read())
        }).json()["project_id"]
    dr = client.post("/api/upload", files={"file0": ("filech1_0", _read("filech1_0"))}).json()["project_id"]
    return ut, dr


def test_two_worlds_grounding_pure():
    import crossave
    cur = {"name": "Kris", "route": "undetermined", "game": "deltarune"}
    priors = [{"name": "Frisk", "route": "Pacifist", "love": 1, "game": "undertale"}]
    g = crossave.build_two_worlds_grounding(cur, priors, voice="toriel")
    assert "ACROSS TWO WORLDS" in g and "Undertale" in g and "Frisk" in g
    assert "NEVER assert" in g
    # gated: only the returning faces feel it; same-game priors never fire it
    assert crossave.build_two_worlds_grounding(cur, priors, voice="jevil") == ""
    assert crossave.build_two_worlds_grounding(cur, [{"game": "deltarune"}], voice="toriel") == ""


def test_two_worlds_in_chat_prompt(monkeypatch):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "ok", "model": "m"})
    ut, dr = _tw_setup()
    # DR save + UT prior → Hometown Toriel dreams of the Underground
    client.post(f"/api/projects/{dr}/chat", json={"character": "toriel", "message": "hi", "history": []})
    assert "ACROSS TWO WORLDS" in seen["prompt"]
    # a Darkner never gets the block
    client.post(f"/api/projects/{dr}/chat", json={"character": "susie", "message": "hi", "history": []})
    assert "ACROSS TWO WORLDS" not in seen["prompt"]
    # and the other direction: UT save + DR prior → Underground Toriel feels it too
    client.post(f"/api/projects/{ut}/chat", json={"character": "toriel", "message": "hi", "history": []})
    assert "ACROSS TWO WORLDS" in seen["prompt"]


def test_recognition_endpoint_reports_two_worlds():
    ut, dr = _tw_setup()
    rec = client.get(f"/api/projects/{dr}/recognition").json()
    assert rec["two_worlds_present"] is True
    assert rec["current_game"] == "deltarune"
    assert rec["other_world"]["game"] == "undertale"


def test_cross_world_divergence_names_both_worlds(monkeypatch):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "two worlds, one hand.", "model": "m"})
    ut, dr = _tw_setup()
    r = client.post("/api/divergence", json={"project_a": ut, "project_b": dr, "character": "sans"}).json()
    assert r["author"] == "Sans"
    assert "TWO WORLDS" in seen["prompt"]
    assert "Undertale, the Underground" in seen["prompt"]
    assert "Deltarune, the Dark World" in seen["prompt"]
