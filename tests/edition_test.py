"""The lite/pro edition switch — Spark-locked lite, untouched pro."""
import power_config


def test_lite_locks_to_spark(monkeypatch, tmp_path):
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    monkeypatch.setenv("EMBER_EDITION", "lite")
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")
    assert power_config.source() == "none"          # env can't unlock it
    power_config.save({"source": "anthropic"})
    assert power_config.source() == "none"          # neither can the config
    st = power_config.public_state()
    assert st["edition"] == "lite" and st["source"] == "none"


def test_pro_is_default_and_unchanged(monkeypatch, tmp_path):
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    monkeypatch.delenv("EMBER_EDITION", raising=False)
    monkeypatch.setenv("UNDERTALE_VERA_BACKEND", "ollama")
    assert power_config.edition() == "pro"
    assert power_config.source() == "ollama"
    monkeypatch.setenv("EMBER_EDITION", "hamster")   # nonsense → pro
    assert power_config.edition() == "pro"


def test_pro_url_rides_public_state(monkeypatch, tmp_path):
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    monkeypatch.setenv("EMBER_EDITION", "lite")
    monkeypatch.setenv("EMBER_PRO_URL", "https://example.com/pro")
    assert power_config.public_state()["pro_url"] == "https://example.com/pro"


def test_power_lock_refuses_changes(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import undertale_vera_app as appmod
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    monkeypatch.setenv("EMBER_POWER_LOCK", "1")
    c = TestClient(appmod.app)
    assert c.get("/api/power").json()["locked"] is True
    assert c.post("/api/power", json={"source": "none"}).status_code == 403
    monkeypatch.delenv("EMBER_POWER_LOCK")
    assert c.post("/api/power", json={"source": "ollama"}).status_code == 200


def test_guided_watch_forbidden_on_any_shared_site(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import undertale_vera_app as appmod
    monkeypatch.setattr(appmod, "VISITOR_SCOPE", True)   # shared pro deployment
    c = TestClient(appmod.app)
    assert c.post("/api/guided/watch", json={"path": str(tmp_path)}).status_code == 403


def test_shared_sites_refuse_visitor_power_writes(monkeypatch, tmp_path):
    """No env flag to forget: lite and visitor-scoped sites refuse by construction."""
    from fastapi.testclient import TestClient
    import undertale_vera_app as appmod
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    c = TestClient(appmod.app)
    monkeypatch.setenv("EMBER_EDITION", "lite")
    assert c.post("/api/power", json={"source": "none"}).status_code == 403
    assert c.post("/api/power/detect", json={}).status_code == 403
    monkeypatch.delenv("EMBER_EDITION")
    monkeypatch.setenv("EMBER_VISITOR_SCOPE", "1")
    assert c.post("/api/power", json={"source": "none"}).status_code == 403
    assert c.post("/api/power/detect", json={}).status_code == 403
    monkeypatch.delenv("EMBER_VISITOR_SCOPE")
    assert c.post("/api/power", json={"source": "none"}).status_code == 200


def test_shared_sites_hide_config_details(monkeypatch, tmp_path):
    """A visitor's browser gets the source, never the wiring — not even masked."""
    import json
    monkeypatch.setattr(power_config, "CONFIG_PATH", str(tmp_path / "p.json"))
    power_config.save({"source": "openrouter",
                       "openrouter_key": "sk-or-v1-supersecret4242",
                       "ollama_host": "http://gpu-box:11434"})
    monkeypatch.setenv("EMBER_EDITION", "lite")
    st = power_config.public_state()
    assert st["locked"] is True
    assert st["openrouter_key"] is None and st["ollama_host"] is None
    dumped = json.dumps(st)
    assert "supersecret" not in dumped and "gpu-box" not in dumped
    # the owner's own (non-shared) install still sees its saved config, masked
    monkeypatch.delenv("EMBER_EDITION")
    st = power_config.public_state()
    assert st["locked"] is False
    assert st["ollama_host"] == "http://gpu-box:11434"
    assert st["openrouter_key"].startswith("sk-or-v") and "supersecret" not in st["openrouter_key"]
