"""Issue #1: configuration loading (CHAT-NF-007; SAD configuration settings)."""
import json
import os

import pytest

from server.config import DEFAULTS, PROJECT_ROOT, ConfigError, load_config


def write_config(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_defaults_match_example_config():
    with open(PROJECT_ROOT / "config.example.json", encoding="utf-8") as f:
        assert json.load(f) == DEFAULTS


def test_file_values_override_defaults(tmp_path):
    config = load_config(write_config(tmp_path, {"port": 6000, "max_frame_bytes": 4096}))
    assert config["port"] == 6000
    assert config["max_frame_bytes"] == 4096
    assert config["max_text_chars"] == DEFAULTS["max_text_chars"]


def test_keyword_overrides_win(tmp_path):
    config = load_config(write_config(tmp_path, {"port": 6000}), port=7000)
    assert config["port"] == 7000


def test_relative_paths_resolve_to_project_root(tmp_path):
    config = load_config(write_config(tmp_path, {}))
    assert config["db_path"] == os.path.join(str(PROJECT_ROOT), "data", "chat.db")


@pytest.mark.parametrize("bad", [
    {"port": 70000},
    {"port": "5050"},
    {"port": True},
    {"max_frame_bytes": 0},
    {"host": ""},
    {"prot": 5050},
])
def test_invalid_settings_are_rejected(tmp_path, bad):
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, bad))


def test_unreadable_file_is_reported(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
