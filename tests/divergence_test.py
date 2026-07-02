"""Two-Save Divergence — a character reflects on the fork between any two saves."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import divergence as divergence_mod
from llm_client import LLMUnavailable


client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


# ── pure module ──────────────────────────────────────────────────────────────

def test_two_file_block_names_both_files():
    a = {"name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0}
    b = {"name": "Chara", "love": 20, "route": "Genocide", "total_kills": 9}
    block = divergence_mod.two_file_block(a, b)
    assert "FILE ONE" in block and "FILE TWO" in block
    assert "Pacifist" in block and "Genocide" in block and "NEVER OVERRIDE OR INVENT" in block


def test_fallback_names_the_fork():
    a = {"name": "Frisk", "love": 1, "route": "Pacifist", "total_kills": 0}
    b = {"name": "Chara", "love": 20, "route": "Genocide", "total_kills": 9}
    f = divergence_mod.fallback("Sans", a, b)
    assert "Sans" in f and "Pacifist" in f and "Genocide" in f


def test_fallback_same_route_and_missing():
    same = divergence_mod.fallback("Toriel", {"route": "Neutral"}, {"route": "Neutral"})
    assert "same road" in same.lower()
    missing = divergence_mod.fallback("Toriel", {"route": "Pacifist"}, {"route": None})
    assert "enough" in missing.lower()


# ── endpoint ─────────────────────────────────────────────────────────────────

def test_divergence_endpoint(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "one path you spared; the other you did not.", "model": "m"})
    pa = _upload("file0_pacifist", "undertale_pacifist.ini")
    pb = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post("/api/divergence", json={"project_a": pa, "project_b": pb, "character": "sans"}).json()
    assert r["author"] == "Sans"
    assert "spared" in r["text"]
    assert r["grounding_source"] == "llm"
    assert r["a"]["route"] == "Pacifist" and r["b"]["route"] == "Genocide"


def test_divergence_hands_both_saves_to_the_model(monkeypatch):
    seen = {}
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: seen.update(prompt=sp) or {"text": "x", "model": "m"})
    pa = _upload("file0_pacifist", "undertale_pacifist.ini")
    pb = _upload("file0_genocide", "undertale_genocide.ini")
    client.post("/api/divergence", json={"project_a": pa, "project_b": pb, "character": "toriel"})
    assert "FILE ONE" in seen["prompt"] and "FILE TWO" in seen["prompt"]
    assert "Pacifist" in seen["prompt"] and "Genocide" in seen["prompt"]


def test_divergence_falls_back_without_model(monkeypatch):
    def boom(*a, **k):
        raise LLMUnavailable("no model")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    pa = _upload("file0_pacifist", "undertale_pacifist.ini")
    pb = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post("/api/divergence", json={"project_a": pa, "project_b": pb, "character": "flowey"}).json()
    assert r["grounding_source"] == "deterministic_fallback"
    assert "Pacifist" in r["text"] and "Genocide" in r["text"]


def test_divergence_404s(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "x", "model": "m"})
    pa = _upload("file0_neutral", "undertale_neutral.ini")
    assert client.post("/api/divergence", json={"project_a": pa, "project_b": 99999, "character": "sans"}).status_code == 404
    assert client.post("/api/divergence", json={"project_a": pa, "project_b": pa, "character": "nobody"}).status_code == 404
