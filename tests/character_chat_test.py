"""Grounded character chat: grounding references ONLY real save facts; LLM mocked."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        resp = client.post(
            "/api/upload",
            files={"file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())},
        )
    assert resp.status_code == 200, resp.text
    return resp.json()["project_id"]


def test_grounding_references_only_real_route(monkeypatch):
    captured = {}

    def fake_generate_reply(system_prompt, user_message, **kwargs):
        captured["system_prompt"] = system_prompt
        return {"text": "heya. your save says it all.", "model": "mock", "stop_reason": "end_turn"}

    # Patch the reference the app actually calls.
    monkeypatch.setattr(appmod, "generate_reply", fake_generate_reply)

    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "who am I?"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    sp = captured["system_prompt"]
    # Sacred facts present; the route is the REAL one, not a guess.
    assert "Pacifist" in sp
    assert "Genocide" not in sp
    assert data["route"] == "Pacifist"
    assert data["response"] == "heya. your save says it all."


def test_undetermined_route_is_told_to_the_model(monkeypatch):
    captured = {}

    def fake(sp, um, **k):
        captured["sp"] = sp
        return {"text": "hm.", "model": "mock"}

    monkeypatch.setattr(appmod, "generate_reply", fake)
    # An unreadable LOVE keeps the route honest even when an ini is present.
    pid2 = _upload("file0_ambiguous", "undertale_pacifist.ini")
    resp = client.post(f"/api/projects/{pid2}/chat", json={"character": "sans", "message": "?"})
    assert resp.status_code == 200
    # The route block must instruct the model not to claim a route.
    assert "UNDETERMINED" in captured["sp"].upper()


def test_unknown_character_is_rejected():
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "nobody", "message": "hi"})
    assert resp.status_code == 404


def test_graceful_degradation_without_model(monkeypatch):
    from llm_client import LLMUnavailable

    def boom(*a, **k):
        raise LLMUnavailable("no model")

    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding"]["source"] == "deterministic_fallback"
    assert "Genocide" in data["response"]  # stays grounded, honest
