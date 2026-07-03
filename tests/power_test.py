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


def test_ollama_config_round_trip(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    r = client.post("/api/power", json={"source": "ollama",
                                        "ollama_host": "http://gpu-box:11434/",
                                        "ollama_model": "qwen3:14b"}).json()
    assert r["ollama_host"] == "http://gpu-box:11434"   # trailing slash stripped
    assert r["ollama_model"] == "qwen3:14b"
    # config wins over env
    monkeypatch.setenv("OLLAMA_HOST", "http://elsewhere:1")
    monkeypatch.setenv("OLLAMA_MODEL", "other")
    assert power_config.ollama_host() == "http://gpu-box:11434"
    assert power_config.ollama_model() == "qwen3:14b"
    # bad host scheme rejected
    assert client.post("/api/power", json={"source": "ollama",
                                           "ollama_host": "file:///etc/passwd"}).status_code == 400


def test_ollama_env_fallback_unchanged(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)                          # fresh config: nothing saved
    monkeypatch.setenv("OLLAMA_HOST", "http://box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    assert power_config.ollama_host() == "http://box:11434"
    assert power_config.ollama_model() == "llama3.2:3b"
    monkeypatch.delenv("OLLAMA_HOST")
    monkeypatch.delenv("OLLAMA_MODEL")
    assert power_config.ollama_host() == power_config.OLLAMA_DEFAULT_HOST
    assert power_config.ollama_model() == power_config.OLLAMA_DEFAULT_MODEL


def test_ollama_model_from_config_reaches_payload(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    power_config.save({"source": "ollama", "ollama_host": "http://gpu-box:11434",
                       "ollama_model": "qwen3:14b"})
    seen = {}

    def fake_chat(payload):
        seen.update(payload=payload)
        return {"message": {"content": "hey."}, "model": payload["model"]}

    monkeypatch.setattr(llm_client, "_ollama_chat", fake_chat)
    r = llm_client.generate_reply("sys", "hello")
    assert r["text"] == "hey."
    assert seen["payload"]["model"] == "qwen3:14b"
    assert llm_client._ollama_host() == "http://gpu-box:11434"


def test_custom_backend(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    power_config.save({"source": "custom", "custom_base_url": "http://127.0.0.1:8000/v1",
                       "custom_model": "local-qwen", "custom_key": "sk-local-abcdefgh12345678"})
    seen = {}

    def fake_chat(payload, base_url, key):
        seen.update(payload=payload, base_url=base_url, key=key)
        return {"choices": [{"message": {"content": "hey."}, "finish_reason": "stop"}],
                "model": payload["model"]}

    monkeypatch.setattr(llm_client, "_custom_chat", fake_chat)
    r = llm_client.generate_reply("sys prompt", "hello")
    assert r["text"] == "hey." and r["model"] == "local-qwen"
    assert seen["base_url"] == "http://127.0.0.1:8000/v1"
    assert seen["key"] == "sk-local-abcdefgh12345678"
    assert seen["payload"]["messages"][0] == {"role": "system", "content": "sys prompt"}


def test_custom_requires_base_url(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    monkeypatch.delenv("EMBER_CUSTOM_BASE_URL", raising=False)
    assert client.post("/api/power", json={"source": "custom"}).status_code == 400
    # and at generate time an unset URL degrades, never crashes
    import pytest
    power_config.save({"source": "custom"})
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("sys", "hi")


def test_custom_key_masked(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    r = client.post("/api/power", json={"source": "custom",
                                        "custom_base_url": "http://127.0.0.1:8000/v1",
                                        "custom_model": "local-qwen",
                                        "custom_key": "sk-local-abcdefgh12345678"}).json()
    assert "abcdefgh" not in json.dumps(r)               # never echoed raw
    assert r["custom_key"].startswith("sk-loca")         # masked prefix only
    g = client.get("/api/power").json()
    assert g["custom_base_url"] == "http://127.0.0.1:8000/v1"
    assert g["custom_model"] == "local-qwen"


def test_custom_unreachable_degrades(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    power_config.save({"source": "custom", "custom_base_url": "http://127.0.0.1:8000/v1",
                       "custom_model": "local-qwen"})

    def boom(payload, base_url, key):
        raise ConnectionError("refused")

    monkeypatch.setattr(llm_client, "_custom_chat", boom)
    import pytest
    with pytest.raises(llm_client.LLMUnavailable):
        llm_client.generate_reply("sys", "hi")


def test_detect_lists_models(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(llm_client, "list_ollama_models",
                        lambda host: ["llama3.1:8b", "qwen3:14b"])
    r = client.post("/api/power/detect", json={"host": "http://127.0.0.1:11434"}).json()
    assert r == {"ok": True, "models": ["llama3.1:8b", "qwen3:14b"]}

    def down(host):
        raise llm_client.LLMUnavailable(f"Ollama not reachable at {host}: refused")

    monkeypatch.setattr(llm_client, "list_ollama_models", down)
    resp = client.post("/api/power/detect", json={})
    assert resp.status_code == 200                       # honest body, never a 500
    assert resp.json()["ok"] is False and "not reachable" in resp.json()["error"]


def test_detect_gates(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    monkeypatch.setenv("EMBER_POWER_LOCK", "1")
    assert client.post("/api/power/detect", json={}).status_code == 403
    monkeypatch.delenv("EMBER_POWER_LOCK")
    monkeypatch.setattr(appmod, "VISITOR_SCOPE", True)
    assert client.post("/api/power/detect", json={}).status_code == 403
    monkeypatch.setattr(appmod, "VISITOR_SCOPE", False)
    for bad in ("ftp://x", "file:///etc/passwd", "not a url"):
        assert client.post("/api/power/detect", json={"host": bad}).status_code == 400
