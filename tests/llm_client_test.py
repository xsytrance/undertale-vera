"""LLM client degradation — running with no/invalid credentials must NEVER 500.

Regression for the live bug: with the anthropic SDK installed but ANTHROPIC_API_KEY
unset, anthropic.Anthropic() raises at construction; that has to surface as
LLMUnavailable so the chat endpoint returns a grounded deterministic reply (200),
not a plain-text 500 that the frontend can't parse."""
import os
import sys
import types

import pytest
from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import llm_client

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _fake_anthropic_module(raise_on_construct):
    """A stand-in `anthropic` module whose Anthropic() raises — mimics no key."""
    mod = types.ModuleType("anthropic")

    class AnthropicError(Exception):
        pass

    def Anthropic(*a, **k):
        raise AnthropicError(raise_on_construct)

    mod.AnthropicError = AnthropicError
    mod.Anthropic = Anthropic
    return mod


# ── unit ─────────────────────────────────────────────────────────────────────

def test_make_client_without_key_degrades(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic",
                        _fake_anthropic_module("The api_key client option must be set"))
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client._make_client()


def test_generate_reply_degrades_on_request_failure():
    class BoomClient:
        class messages:
            @staticmethod
            def create(**k):
                raise RuntimeError("502 upstream / no network")

    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("system", "hi", client=BoomClient())


# ── end-to-end: the exact bug from the screenshot ────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_chat_without_key_returns_grounded_fallback_not_500(monkeypatch):
    # SDK present, no key → construction raises. Do NOT mock generate_reply:
    # exercise the real degrade path the live app takes.
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic_module("no api key"))
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    resp = client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "what's up sans?"})
    assert resp.status_code == 200                      # not a 500
    data = resp.json()
    assert data["grounding"]["source"] == "deterministic_fallback"
    assert "Genocide" in data["response"]               # still grounded, honest
