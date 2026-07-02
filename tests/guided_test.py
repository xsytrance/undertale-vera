"""Guided Mode — the save watcher: discovery, adoption, settled-change beats."""
import os
import shutil

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import guided


client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _fresh_state():
    appmod.guided_state.dirs = []
    appmod.guided_state.files = {}


# ── pure ─────────────────────────────────────────────────────────────────────

def test_discover_and_sibling(tmp_path):
    (tmp_path / "file0").write_text("x")
    (tmp_path / "undertale.ini").write_text("[General]\n")
    (tmp_path / "filech1_0").write_text("y")
    (tmp_path / "filech1_9").write_text("z")     # backup slot: not watched
    (tmp_path / "config.ini").write_text("no")
    found = [os.path.basename(p) for p in guided.discover_saves(str(tmp_path))]
    assert found == ["file0", "filech1_0"]
    assert guided.sibling_ini(str(tmp_path / "file0")).endswith("undertale.ini")
    assert guided.sibling_ini(str(tmp_path / "filech1_0")) is None   # no dr.ini here


def test_digest_includes_sibling(tmp_path):
    (tmp_path / "file0").write_text("same")
    d1 = guided.digest_file(str(tmp_path / "file0"))
    (tmp_path / "undertale.ini").write_text("[General]\nGold=1\n")
    d2 = guided.digest_file(str(tmp_path / "file0"))
    assert d1 and d2 and d1 != d2     # the ini rides the digest


# ── the scan loop (adopt → settle → beat) ────────────────────────────────────

def test_watch_adopts_and_beats_on_settled_change(tmp_path):
    _fresh_state()
    shutil.copy(os.path.join(FIX, "filech1_0_early"), tmp_path / "filech1_0")
    r = client.post("/api/guided/watch", json={"path": str(tmp_path)}).json()
    assert str(tmp_path) in r["watching"][0]
    assert len(r["adopted"]) == 1 and r["adopted"][0]["type"] == "adopted"
    pid = r["adopted"][0]["project_id"]
    assert r["adopted"][0]["game"] == "deltarune"

    # overwrite with the completed save → first scan arms (settle), second beats
    shutil.copy(os.path.join(FIX, "filech1_0_completed"), tmp_path / "filech1_0")
    db = appmod.SessionLocal()
    try:
        assert appmod.guided_scan_once(db) == []          # pending (write settling)
        beats = appmod.guided_scan_once(db)               # settled → the beat
    finally:
        db.close()
    assert len(beats) == 1
    b = beats[0]
    assert b["type"] == "save" and b["project_id"] == pid and b["visit"] == 2
    # the project's truth advanced to the completed save
    t = client.get(f"/api/projects/{pid}/save-truth").json()["save_truth"]
    assert t["deltarune"]["jevil_defeated"] is True
    assert t["play_state"]["gold"] == 3000


def test_unwatch_and_status(tmp_path):
    _fresh_state()
    shutil.copy(os.path.join(FIX, "filech1_0_early"), tmp_path / "filech1_0")
    client.post("/api/guided/watch", json={"path": str(tmp_path)})
    st = client.get("/api/guided/status").json()
    assert len(st["watching"]) == 1 and st["files"][0]["file"] == "filech1_0"
    client.request("DELETE", "/api/guided/watch", json={"path": str(tmp_path)})
    st2 = client.get("/api/guided/status").json()
    assert st2["watching"] == []


def test_watch_rejects_non_directory():
    _fresh_state()
    assert client.post("/api/guided/watch", json={"path": "/nope/definitely/not"}).status_code == 400


def test_undertale_save_watch(tmp_path):
    _fresh_state()
    shutil.copy(os.path.join(FIX, "file0_pacifist"), tmp_path / "file0")
    shutil.copy(os.path.join(FIX, "undertale_pacifist.ini"), tmp_path / "undertale.ini")
    r = client.post("/api/guided/watch", json={"path": str(tmp_path)}).json()
    assert r["adopted"][0]["game"] == "undertale"
    assert r["adopted"][0]["route"] == "Pacifist"
    _fresh_state()


# ── delta-aware reactions + the hint ladder ──────────────────────────────────

def _upload(stem, ini=None):
    files = {"file0": (stem if stem.startswith("filech") else "file0",
                       open(os.path.join(FIX, stem), "rb").read())}
    if ini:
        files["undertale_ini"] = ("undertale.ini", open(os.path.join(FIX, ini), "rb").read())
    return client.post("/api/upload", files=files).json()["project_id"]


def test_guided_react_speaks_to_the_delta(monkeypatch):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp, um=um) or {"text": "you crossed a line back there.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/guided-react",
                    json={"character": "sans", "changes": ["LOVE rose from 1 to 5", "kills went from 0 to 3"]}).json()
    assert r["character"] == "Sans" and "crossed" in r["message"]
    assert "BETWEEN THEIR LAST TWO SAVES" in seen["prompt"]
    assert "kills went from 0 to 3" in seen["prompt"]
    # persisted to the transcript as an unprompted turn
    convo = client.get(f"/api/projects/{pid}/conversations/sans").json()
    assert any(m.get("unprompted") for m in convo["messages"])


def test_guided_react_fallback_names_changes(monkeypatch):
    from llm_client import LLMUnavailable
    def boom(*a, **k): raise LLMUnavailable("x")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    r = client.post(f"/api/projects/{pid}/guided-react",
                    json={"character": "toriel", "changes": ["gold rose from 0 to 120"]}).json()
    assert r["grounding_source"] == "deterministic_fallback"
    assert "gold rose" in r["message"]


def test_hint_ladder_undertale():
    import guide_kb
    t = {"game": "undertale", "play_state": {"room_name": "Snowdin Town", "room": None}}
    for lvl in ("nudge", "hint", "tell"):
        h = guide_kb.hint_for(t, lvl)
        assert h["level"] == lvl and h["where"] == "Snowdin" and h["text"]
    # tell says more than nudge
    assert len(guide_kb.hint_for(t, "tell")["text"]) > len(guide_kb.hint_for(t, "nudge")["text"])


def test_hint_stages_deltarune():
    import guide_kb
    full = {"game": "deltarune", "deltarune": {"party": ["Kris", "Susie", "Ralsei"], "jevil_defeated": False}}
    assert guide_kb.hint_for(full, "hint")["stage"] == "full_party"
    done = {"game": "deltarune", "deltarune": {"party": ["Kris", "Susie", "Ralsei"], "jevil_defeated": True}}
    assert guide_kb.hint_for(done, "nudge")["stage"] == "jevil_done"
    unknown = {"game": "deltarune", "deltarune": {}}
    assert "can't tell" in guide_kb.hint_for(unknown, "tell")["text"] or "save" in guide_kb.hint_for(unknown, "tell")["text"].lower()


def test_guided_hint_endpoint_in_voice_and_fallback(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "heya. keep east, the fog's the way.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/guided-hint", json={"level": "hint", "character": "sans"}).json()
    assert r["speaker"] == "Sans" and "east" in r["text"] and r["plain"]
    # no character → the plain, honest hint
    r2 = client.post(f"/api/projects/{pid}/guided-hint", json={"level": "tell"}).json()
    assert r2["speaker"] is None and r2["text"] == r2["plain"]


# ── session stories ──────────────────────────────────────────────────────────

def test_session_story_pure():
    import session_story
    snaps = [
        {"counter": 1, "name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0},
        {"counter": 2, "name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0},
        {"counter": 3, "name": "Frisk", "love": 3, "route": "Neutral", "total_kills": 4},
    ]
    beats = session_story.session_beats(snaps)
    assert len(beats) == 2 and beats[0]["changes"]           # quiet save still a beat
    block = session_story.story_block(snaps)
    assert "It began" in block and "It stands now" in block and "NEVER OVERRIDE" in block
    fb = session_story.fallback("Sans", snaps)
    assert "Sans" in fb and "2 beats" in fb


def test_session_story_endpoint(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "you walked in quiet, you left quieter.", "model": "m"})
    _fresh_state()
    shutil.copy(os.path.join(FIX, "filech1_0_early"), tmp_path / "filech1_0")
    r = client.post("/api/guided/watch", json={"path": str(tmp_path)}).json()
    pid = r["adopted"][0]["project_id"]
    shutil.copy(os.path.join(FIX, "filech1_0_completed"), tmp_path / "filech1_0")
    db = appmod.SessionLocal()
    try:
        appmod.guided_scan_once(db); appmod.guided_scan_once(db)
    finally:
        db.close()
    res = client.post(f"/api/projects/{pid}/session-story", json={"character": "ralsei"}).json()
    assert res["character"] == "Ralsei" and res["visits"] == 2 and len(res["beats"]) == 1
    assert "THE SESSION THE SAVE RECORDS" in seen["prompt"]
    assert "quieter" in res["text"]
    _fresh_state()


def test_watch_state_persists_and_reuses_projects(tmp_path):
    """A server restart must resume watching and REUSE projects — no shelf duplicates."""
    _fresh_state()
    store = tmp_path / "watch_store.json"
    shutil.copy(os.path.join(FIX, "filech1_0_early"), tmp_path / "filech1_0")

    old_store = appmod.guided_state.store_path
    appmod.guided_state.store_path = str(store)
    try:
        r = client.post("/api/guided/watch", json={"path": str(tmp_path)}).json()
        pid = r["adopted"][0]["project_id"]
        assert store.exists()
        # simulate a restart: a fresh WatchState loading the same store
        appmod.guided_state = guided.WatchState(store_path=str(store))
        appmod.guided_state.load()
        assert str(tmp_path) in appmod.guided_state.dirs[0]
        db = appmod.SessionLocal()
        try:
            assert appmod.guided_scan_once(db) == []   # unchanged file → no re-adoption
            # a real change still beats against the SAME project
            shutil.copy(os.path.join(FIX, "filech1_0_completed"), tmp_path / "filech1_0")
            appmod.guided_scan_once(db)
            beats = appmod.guided_scan_once(db)
        finally:
            db.close()
        assert len(beats) == 1 and beats[0]["project_id"] == pid and beats[0]["type"] == "save"
    finally:
        appmod.guided_state = guided.WatchState(store_path=old_store)


def test_deltarune_beats_speak_dark_world(tmp_path):
    """DR saves must beat in the Dark World's own language, not 'quiet save'."""
    from deltarune_truth import deltarune_delta
    prev = {"game": "deltarune", "play_state": {"room": 98},
            "deltarune": {"dark_dollars": 63, "party": ["Kris", "Ralsei"], "jevil_defeated": False}}
    curr = {"game": "deltarune", "play_state": {"room": 403},
            "deltarune": {"dark_dollars": 3000, "party": ["Kris", "Susie", "Ralsei"], "jevil_defeated": True}}
    d = deltarune_delta(prev, curr)
    assert "dark dollars rose from 63 to 3000" in d
    assert "Susie joined the party" in d
    assert any("jester" in x for x in d)
    assert any("room 98 → 403" in x for x in d)

    # end-to-end: the watcher's beat carries these lines
    _fresh_state()
    shutil.copy(os.path.join(FIX, "filech1_0_early"), tmp_path / "filech1_0")
    r = client.post("/api/guided/watch", json={"path": str(tmp_path)}).json()
    shutil.copy(os.path.join(FIX, "filech1_0_completed"), tmp_path / "filech1_0")
    db = appmod.SessionLocal()
    try:
        appmod.guided_scan_once(db)
        beats = appmod.guided_scan_once(db)
    finally:
        db.close()
    ch = beats[0]["changes"]
    assert any("Susie joined" in c for c in ch) and any("dark dollars" in c for c in ch)
    _fresh_state()
