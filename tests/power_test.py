"""The power ladder — source selection, BYOK OpenRouter, Spark mode honesty."""
import json
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import llm_client
import power_config


client = TestClient(appmod.app)


def _cfg(tmp_path, monkeypatch):
    p = str(tmp_path / "ember_power.json")
    monkeypatch.setattr(power_config, "CONFIG_PATH", p)
    return p


def test_source_resolution(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")
    assert power_config.source() == "ollama"           # no config → env
    power_config.save({"source": "none"})
    assert power_config.source() == "none"             # config wins
    st = os.stat(power_config.CONFIG_PATH)
    assert oct(st.st_mode & 0o777) == "0o600"          # key-safe file mode


def test_spark_mode_degrades_to_grounded_fallback(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    power_config.save({"source": "none"})
    import pytest
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("sys", "hi")
    # /api/power/test reports Spark as working-by-design
    r = client.post("/api/power/test").json()
    assert r["ok"] is True and "Spark" in r["sample"]


def test_openrouter_backend(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    power_config.save({"source": "openrouter", "openrouter_key": "sk-or-test-1234567890",
                       "openrouter_model": "deepseek/deepseek-chat"})
    seen = {}

    def fake_chat(payload, key):
        seen.update(payload=payload, key=key)
        return {"choices": [{"message": {"content": "hey."}, "finish_reason": "stop"}],
                "model": payload["model"]}

    monkeypatch.setattr(llm_client, "_openrouter_chat", fake_chat)
    r = llm_client.generate_reply("sys prompt", "hello", history=[{"role": "user", "content": "x"}])
    assert r["text"] == "hey." and r["model"] == "deepseek/deepseek-chat"
    assert seen["key"].startswith("sk-or-test")
    assert seen["payload"]["messages"][0] == {"role": "system", "content": "sys prompt"}


def test_power_endpoints_mask_the_key(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    r = client.post("/api/power", json={"source": "openrouter",
                                        "openrouter_key": "sk-or-v1-abcdefghijklmnop",
                                        "openrouter_model": "google/gemini-flash-1.5"}).json()
    assert r["source"] == "openrouter"
    assert "abcdefghijk" not in json.dumps(r)          # never echoed
    assert r["openrouter_key"].startswith("sk-or-v")   # masked prefix only
    g = client.get("/api/power").json()
    assert g["openrouter_model"] == "google/gemini-flash-1.5"
    assert len(g["suggestions"]) >= 3
    # bad source rejected; openrouter without a key rejected
    assert client.post("/api/power", json={"source": "hamster"}).status_code == 400


def test_openrouter_requires_key(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert client.post("/api/power", json={"source": "openrouter"}).status_code == 400
