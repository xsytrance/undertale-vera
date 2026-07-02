"""LLM client backends + degradation — chat must NEVER 500, on either backend.

Covers the local Ollama backend (default) and the Anthropic backend, and the
regression that an unreachable/unconfigured model degrades to a grounded
deterministic reply (200) instead of a plain-text 500 the frontend can't parse."""
import os
import sys
import types

import pytest
from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import llm_client

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── Ollama backend (default) ─────────────────────────────────────────────────

def test_ollama_reply_parses_message(monkeypatch):
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")
    seen = {}

    def fake_chat(payload):
        seen["payload"] = payload
        return {"message": {"content": "heya. i'm sans."}, "model": "llama3.1:8b", "done_reason": "stop"}

    monkeypatch.setattr(llm_client, "_ollama_chat", fake_chat)
    out = llm_client.generate_reply("SYSTEM", "hi", history=[{"role": "user", "content": "earlier"}])
    assert out["text"] == "heya. i'm sans."
    assert out["model"] == "llama3.1:8b"
    # request shape mirrors fft-psx-vera: system message first, stream off
    msgs = seen["payload"]["messages"]
    assert msgs[0] == {"role": "system", "content": "SYSTEM"}
    assert msgs[-1] == {"role": "user", "content": "hi"}
    assert seen["payload"]["stream"] is False


def test_ollama_unreachable_degrades(monkeypatch):
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")

    def boom(payload):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(llm_client, "_ollama_chat", boom)
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("SYSTEM", "hi")


# ── Anthropic backend ────────────────────────────────────────────────────────

def _fake_anthropic_module(raise_on_construct):
    mod = types.ModuleType("anthropic")

    class AnthropicError(Exception):
        pass

    def Anthropic(*a, **k):
        raise AnthropicError(raise_on_construct)

    mod.AnthropicError = AnthropicError
    mod.Anthropic = Anthropic
    return mod


def test_make_client_without_key_degrades(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic",
                        _fake_anthropic_module("The api_key client option must be set"))
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client._make_client()


def test_generate_reply_degrades_on_request_failure():
    # an injected client forces the Anthropic path regardless of backend
    class BoomClient:
        class messages:
            @staticmethod
            def create(**k):
                raise RuntimeError("502 upstream / no network")

    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("system", "hi", client=BoomClient())


# ── end-to-end: a chat must degrade to a grounded 200, never 500 ─────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_chat_with_ollama_down_returns_grounded_fallback(monkeypatch):
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")
    monkeypatch.setattr(llm_client, "_ollama_chat",
                        lambda payload: (_ for _ in ()).throw(ConnectionError("refused")))
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "what route am i on?"})
    assert resp.status_code == 200                      # not a 500
    data = resp.json()
    assert data["grounding"]["source"] == "deterministic_fallback"
    assert "Genocide" in data["response"]               # still grounded, honest


def test_chat_without_key_returns_grounded_fallback_not_500(monkeypatch):
    # SDK present, no key, Anthropic backend → construction raises; do NOT mock
    # generate_reply: exercise the real degrade path the live app takes.
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "anthropic")
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic_module("no api key"))
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "what route am i on?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding"]["source"] == "deterministic_fallback"
    assert "Genocide" in data["response"]
