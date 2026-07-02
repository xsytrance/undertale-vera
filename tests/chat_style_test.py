"""Chat style options — the player's FREE dials for HOW a character answers."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from chat_style import build_style_directives, lore_k

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── pure ─────────────────────────────────────────────────────────────────────

def test_default_options_produce_no_directives():
    assert build_style_directives({}) == ""
    assert build_style_directives({"verbosity": "normal", "intensity": "normal", "meta": "subtle"}) == ""


def test_directives_render():
    d = build_style_directives({"verbosity": "brief", "intensity": "dramatic", "meta": "on"})
    assert "very short" in d and "Lean fully" in d and "knowingly about the save" in d
    assert "HOW TO ANSWER" in d
    assert "Do NOT reference" in build_style_directives({"meta": "off"})


def test_lore_k_mapping():
    assert lore_k({}) == 4
    assert lore_k({"lore": "none"}) is None
    assert lore_k({"lore": "light"}) == 2
    assert lore_k({"lore": "rich"}) == 6


# ── chat endpoint wiring ─────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def _chat(pid, **body):
    body.setdefault("character", "sans")
    body.setdefault("message", "hi")
    return client.post(f"/api/projects/{pid}/chat", json=body).json()


def test_chat_default_has_no_style_block(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    assert "HOW TO ANSWER" not in _chat(pid)["grounding"]["system_prompt"]


def test_chat_brief_option_adds_directive(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    sp = _chat(pid, options={"verbosity": "brief"})["grounding"]["system_prompt"]
    assert "very short" in sp


def test_chat_meta_off_suppresses_meta(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    sp = _chat(pid, options={"meta": "off"})["grounding"]["system_prompt"]
    assert "Do NOT reference" in sp


def test_chat_lore_none_drops_lore_layer(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    # lore=rich pulls lore in; lore=none must not.
    rich = _chat(pid, message="tell me about waterfall", options={"lore": "rich"})["provenance"]["free"]["lore"]
    none = _chat(pid, message="tell me about waterfall", options={"lore": "none"})["provenance"]["free"]["lore"]
    assert none == []
