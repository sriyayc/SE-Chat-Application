"""Server entry point: python -m server.main [--config PATH] [--host HOST] [--port PORT]"""
import argparse
import logging
import logging.handlers
import os
import sys

from server.app import ChatServer
from server.config import ConfigError, load_config

log = logging.getLogger("server")


def configure_logging(config):
    os.makedirs(os.path.dirname(config["log_path"]), exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        config["log_path"], maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    console = logging.StreamHandler()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (file_handler, console):
        handler.setFormatter(fmt)
        root.addHandler(handler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chat server")
    parser.add_argument("--config", help="path to config.json (default: ./config.json if present)")
    parser.add_argument("--host", help="override the configured listen address")
    parser.add_argument("--port", type=int, help="override the configured port")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    overrides = {k: v for k, v in (("host", args.host), ("port", args.port)) if v is not None}
    try:
        config = load_config(args.config, **overrides)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    configure_logging(config)
    server = ChatServer(config)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    except OSError as e:
        log.error("cannot listen on %s:%s: %s", config["host"], config["port"], e)
        return 1
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
