import json, os, pytest
from unittest.mock import patch

def test_default_config():
    from config import AppConfig, SanitizationConfig
    cfg = AppConfig()
    assert cfg.provider == "deepl"
    assert cfg.batch_delay_ms == 200
    assert cfg.sanitization.remove_illegal is True
    assert cfg.sanitization.remove_emoji is True
    assert ".mp4" in cfg.file_extensions

def test_save_and_load(tmp_path):
    from config import AppConfig, CONFIG_FILE, CONFIG_DIR
    with patch("config.CONFIG_DIR", str(tmp_path)), \
         patch("config.CONFIG_FILE", str(tmp_path / "config.json")):
        from config import AppConfig
        cfg = AppConfig()
        cfg.deepl_key = "test-key"
        cfg.save()
        loaded = AppConfig.load()
        assert loaded.deepl_key == "test-key"

def test_load_returns_default_on_missing_file(tmp_path):
    with patch("config.CONFIG_FILE", str(tmp_path / "nonexistent.json")):
        from config import AppConfig
        cfg = AppConfig.load()
        assert cfg.provider == "deepl"

def test_load_returns_default_on_corrupt_file(tmp_path):
    bad = tmp_path / "config.json"
    bad.write_text("not json")
    with patch("config.CONFIG_FILE", str(bad)):
        from config import AppConfig
        cfg = AppConfig.load()
        assert cfg.provider == "deepl"
