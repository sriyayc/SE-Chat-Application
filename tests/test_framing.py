"""Issue #4: message framing and safe rejection of bad frames (CHAT-F-009, CHAT-SR-004; TC-MSG-03, TC-SEC-05)."""
import json
import socket
import struct
import threading
import time

import pytest

from server.protocol.framing import (
    HEADER, ConnectionClosed, FrameError, FrameTooLarge, discard, encode, read_frame, recv_exact,
)


@pytest.fixture
def pair():
    a, b = socket.socketpair()
    a.settimeout(5)
    b.settimeout(5)
    yield a, b
    a.close()
    b.close()


def raw_frame(body: bytes):
    return struct.pack(">I", len(body)) + body


def test_encode_uses_big_endian_length_prefix():
    frame = encode({"type": "PING"})
    (length,) = struct.unpack(">I", frame[:4])
    assert length == len(frame) - 4
    assert json.loads(frame[4:]) == {"type": "PING"}


def test_round_trip_keeps_unicode(pair):
    a, b = pair
    message = {"type": "MSG", "payload": {"text": "héllo 👋 नमस्ते"}}
    a.sendall(encode(message))
    assert read_frame(b, 8192) == message


def test_partial_reads_are_reassembled(pair):
    a, b = pair
    data = encode({"type": "MSG", "payload": {"text": "x" * 500}}) + encode({"type": "PING"})

    def trickle():
        for i in range(len(data)):
            a.send(data[i:i + 1])
            if i % 50 == 0:
                time.sleep(0.001)

    threading.Thread(target=trickle).start()
    assert read_frame(b, 8192)["payload"]["text"] == "x" * 500
    assert read_frame(b, 8192) == {"type": "PING"}


def test_back_to_back_frames_in_one_packet(pair):
    a, b = pair
    a.sendall(encode({"n": 1}) + encode({"n": 2}) + encode({"n": 3}))
    assert [read_frame(b, 8192)["n"] for _ in range(3)] == [1, 2, 3]


def test_oversized_frame_rejected_before_body_is_read(pair):
    a, b = pair
    a.sendall(HEADER.pack(8193))  # no body sent at all
    with pytest.raises(FrameTooLarge) as info:
        read_frame(b, 8192)
    assert info.value.length == 8193


def test_frame_at_exact_limit_is_accepted(pair):
    a, b = pair
    body = json.dumps({"t": "x" * 100}).encode()
    a.sendall(raw_frame(body))
    assert read_frame(b, len(body)) == {"t": "x" * 100}


@pytest.mark.parametrize("body", [
    b"{not json",
    b"",
    b"\xff\xfe\x00",          # not UTF-8
    b"[1, 2, 3]",             # JSON, but not an object
    b'"just a string"',
])
def test_malformed_bodies_are_rejected(pair, body):
    a, b = pair
    a.sendall(raw_frame(body))
    with pytest.raises(FrameError):
        read_frame(b, 8192)


def test_stream_stays_in_sync_after_malformed_body(pair):
    a, b = pair
    a.sendall(raw_frame(b"{oops") + encode({"ok": True}))
    with pytest.raises(FrameError):
        read_frame(b, 8192)
    assert read_frame(b, 8192) == {"ok": True}


def test_eof_mid_frame_is_reported(pair):
    a, b = pair
    a.sendall(HEADER.pack(100) + b"{partial")
    a.close()
    with pytest.raises(ConnectionClosed):
        read_frame(b, 8192)


def test_recv_exact_and_discard(pair):
    a, b = pair
    a.sendall(b"abcdefghij")
    discard(b, 4)
    assert recv_exact(b, 6) == b"efghij"


# --- over a real server connection ---

def test_server_rejects_malformed_frame_and_keeps_connection(connect):
    client = connect()
    client.sock.sendall(raw_frame(b"{not json"))
    reply = client.recv()
    assert reply["type"] == "ERROR" and reply["code"] == "INVALID_MESSAGE"
    seq = client.request("PING")
    assert client.recv() == {"type": "PONG", "ref_seq": seq}


def test_server_skips_oversized_frame_and_keeps_connection(connect):
    client = connect()
    client.sock.sendall(raw_frame(b"x" * 20_000))
    reply = client.recv()
    assert reply["type"] == "ERROR" and reply["code"] == "INVALID_MESSAGE"
    seq = client.request("PING")
    assert client.recv() == {"type": "PONG", "ref_seq": seq}


def test_server_closes_connection_on_huge_length_prefix(connect):
    client = connect()
    client.sock.sendall(HEADER.pack(0xFFFFFFFF))
    reply = client.recv()
    assert reply["code"] == "INVALID_MESSAGE"
    with pytest.raises((ConnectionClosed, ConnectionError)):
        client.recv()


def test_bad_client_does_not_affect_others(connect):
    bad, good = connect(), connect()
    bad.sock.sendall(raw_frame(b"\x00garbage") + HEADER.pack(0xFFFFFFFF))
    seq = good.request("PING")
    assert good.recv() == {"type": "PONG", "ref_seq": seq}
