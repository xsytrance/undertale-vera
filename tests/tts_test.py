"""Server-side TTS: the /api/tts contract + graceful degrade when uninstalled.

CI has no .venv-tts/model, so `available()` is False there — these tests assert the
honest-unavailable path and the mapping/gating logic without needing Kokoro.
"""
from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import tts_service


client = TestClient(appmod.app)


def test_voice_for_maps_characters(monkeypatch):
    # pretend the model exposes its real voice set
    monkeypatch.setattr(tts_service, "list_voices", lambda: ["am_onyx", "af_heart", "bm_george"])
    assert tts_service.voice_for("Sans", None) == "am_onyx"          # character map
    assert tts_service.voice_for("Asgore", None) == "bm_george"
    assert tts_service.voice_for("Nobody", None) == tts_service.DEFAULT_VOICE
    assert tts_service.voice_for("Sans", "af_heart") == "af_heart"   # explicit override wins
    assert tts_service.voice_for("Sans", "not_a_voice") == "am_onyx"  # bogus override ignored


def test_health_reports_unavailable(monkeypatch):
    monkeypatch.setattr(tts_service, "available", lambda: False)
    monkeypatch.setattr(appmod.power_config, "shared", lambda: False)
    h = client.get("/api/tts/health").json()
    assert h["available"] is False and h["engine"] is None


def test_synth_503_when_uninstalled(monkeypatch):
    monkeypatch.setattr(tts_service, "available", lambda: False)
    monkeypatch.setattr(appmod.power_config, "shared", lambda: False)
    r = client.post("/api/tts", json={"text": "hello there"})
    assert r.status_code == 503


def test_shared_site_never_synthesizes(monkeypatch):
    # even with an engine present, public/shared deployments must not expose synth
    monkeypatch.setattr(tts_service, "available", lambda: True)
    monkeypatch.setattr(appmod.power_config, "shared", lambda: True)
    assert client.get("/api/tts/health").json()["available"] is False
    assert client.post("/api/tts", json={"text": "hi"}).status_code == 403


def test_synth_returns_wav_when_available(monkeypatch):
    monkeypatch.setattr(appmod.power_config, "shared", lambda: False)
    monkeypatch.setattr(tts_service, "available", lambda: True)
    monkeypatch.setattr(tts_service, "list_voices", lambda: ["am_onyx", "af_heart"])
    monkeypatch.setattr(tts_service, "synth", lambda text, voice=None, speed=1.0: b"RIFF....WAVE-fake")
    r = client.post("/api/tts", json={"text": "heya", "character": "Sans"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["x-ember-voice"] == "am_onyx"       # Sans mapped
    assert r.content == b"RIFF....WAVE-fake"
