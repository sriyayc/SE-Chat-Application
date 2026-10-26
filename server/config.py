"""Server settings: built-in defaults overridden by an optional config.json (see SAD, Configuration settings)."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 5050,
    "max_frame_bytes": 8192,
    "max_text_chars": 2000,
    "max_connections": 100,
    "max_rooms": 50,
    "idle_timeout_seconds": 900,
    "heartbeat_seconds": 30,
    "tls_cert_path": "certs/server.crt",
    "tls_key_path": "certs/server.key",
    "db_path": "data/chat.db",
    "log_path": "logs/server.log",
}

_POSITIVE_INTS = (
    "max_frame_bytes", "max_text_chars", "max_connections",
    "max_rooms", "idle_timeout_seconds", "heartbeat_seconds",
)
_PATHS = ("tls_cert_path", "tls_key_path", "db_path", "log_path")


class ConfigError(ValueError):
    pass


def load_config(path=None, **overrides):
    """Return validated settings.

    Reads `path`, or config.json in the project root if it exists. Unknown keys are
    rejected so typos do not silently fall back to defaults. Relative paths are
    resolved against the project root so the server can be started from any directory.
    """
    config = dict(DEFAULTS)
    if path is None:
        candidate = PROJECT_ROOT / "config.json"
        path = candidate if candidate.exists() else None
    if path is not None:
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ConfigError(f"cannot read config file {path}: {e}") from e
        if not isinstance(loaded, dict):
            raise ConfigError(f"{path} must contain a JSON object")
        config.update(loaded)
    config.update(overrides)
    _validate(config)
    for key in _PATHS:
        p = Path(config[key])
        config[key] = str(p if p.is_absolute() else PROJECT_ROOT / p)
    return config


def _validate(config):
    unknown = set(config) - set(DEFAULTS)
    if unknown:
        raise ConfigError(f"unknown setting(s): {', '.join(sorted(unknown))}")
    if not isinstance(config["host"], str) or not config["host"]:
        raise ConfigError("host must be a non-empty string")
    port = config["port"]
    if not _is_int(port) or not 0 <= port <= 65535:
        raise ConfigError("port must be an integer between 0 and 65535")
    for key in _POSITIVE_INTS:
        if not _is_int(config[key]) or config[key] <= 0:
            raise ConfigError(f"{key} must be a positive integer")
    for key in _PATHS:
        if not isinstance(config[key], str) or not config[key]:
            raise ConfigError(f"{key} must be a non-empty path")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)
