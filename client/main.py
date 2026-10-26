"""Client entry point: python -m client.main [--host HOST] [--port PORT]"""
import argparse
import sys

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chat client")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"server address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"server port (default {DEFAULT_PORT})")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print(f"Chat client: server is {args.host}:{args.port}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
