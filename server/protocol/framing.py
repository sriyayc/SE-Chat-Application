"""Length-prefixed frame reading/writing (recv_exact, max frame size).

Wire format (SAD, Message framing): a 4-byte big-endian unsigned length followed by
that many bytes of UTF-8 JSON. The JSON body must be an object.
"""
import json
import struct

HEADER = struct.Struct(">I")


class ConnectionClosed(Exception):
    """The peer closed the socket (possibly in the middle of a frame)."""


class FrameError(Exception):
    """The frame body is not a valid UTF-8 JSON object. The stream is still in sync."""


class FrameTooLarge(FrameError):
    """The length prefix exceeds the limit. The body has not been read: call discard() to skip it."""

    def __init__(self, message, length):
        super().__init__(message)
        self.length = length


def encode(message, max_bytes=None):
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if max_bytes is not None and len(body) > max_bytes:
        raise FrameTooLarge(f"frame of {len(body)} bytes exceeds {max_bytes}", len(body))
    return HEADER.pack(len(body)) + body


def recv_exact(sock, n):
    """Read exactly n bytes, looping over partial reads; raise ConnectionClosed on EOF."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(n - len(buf), 65536))
        if not chunk:
            raise ConnectionClosed(f"connection closed after {len(buf)} of {n} bytes")
        buf += chunk
    return bytes(buf)


def discard(sock, n):
    """Read and throw away n bytes without buffering them all."""
    while n > 0:
        n -= len(recv_exact(sock, min(n, 65536)))


def read_frame(sock, max_bytes):
    """Read one frame and return the decoded JSON object.

    The length is checked before the body is read, so an oversized frame never
    gets buffered.
    """
    (length,) = HEADER.unpack(recv_exact(sock, HEADER.size))
    if length > max_bytes:
        raise FrameTooLarge(f"frame of {length} bytes exceeds {max_bytes}", length)
    body = recv_exact(sock, length)
    try:
        message = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise FrameError(f"body is not valid UTF-8 JSON: {e}") from e
    if not isinstance(message, dict):
        raise FrameError("body must be a JSON object")
    return message
