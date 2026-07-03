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
