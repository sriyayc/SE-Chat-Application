"""Client entry point: python -m client.main [--host HOST] [--port PORT]"""
import argparse
import queue
import sys
import time

from client.net.connection import ChatConnection

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chat client")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"server address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"server port (default {DEFAULT_PORT})")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    events = queue.Queue()
    conn = ChatConnection(events)
    try:
        conn.connect(args.host, args.port)
    except OSError as e:
        print(f"Could not connect to {args.host}:{args.port}: {e}")
        return 1
    sent = time.monotonic()
    conn.request("PING")
    try:
        while True:
            try:
                item = events.get(timeout=0.5)  # a timeout keeps Ctrl+C responsive on Windows
            except queue.Empty:
                continue
            if item[0] == "disconnected":
                print(f"Disconnected: {item[1]}")
                return 1
            message = item[1]
            if message.get("type") == "PONG" and sent is not None:
                print(f"Connected to {args.host}:{args.port} "
                      f"(round trip {1000 * (time.monotonic() - sent):.1f} ms). Press Ctrl+C to quit.", flush=True)
                sent = None
            elif message.get("type") == "ERROR":
                print(f"Server error {message.get('code')}: {message.get('reason')}", flush=True)
    except KeyboardInterrupt:
        conn.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
