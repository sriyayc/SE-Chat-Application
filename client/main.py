"""Client entry point: python -m client.main [--host HOST] [--port PORT]"""
import argparse
import sys
import tkinter as tk

from client.ui.app import ChatApp

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chat client")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"server address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"server port (default {DEFAULT_PORT})")
    return parser.parse_args(argv)


def enable_sharp_text():
    """Stop Windows from bitmap-scaling the window on high-DPI screens."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main(argv=None):
    args = parse_args(argv)
    enable_sharp_text()
    root = tk.Tk()
    ChatApp(root, args.host, args.port)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
