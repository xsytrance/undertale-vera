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
