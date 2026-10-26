"""Issue #2: TCP client-server connection (CHAT-F-003, CHAT-NF-003; TC-CONN-01, TC-REL-01)."""
import queue
import socket
import time

import pytest

from client.net.connection import ChatConnection
from server.protocol.framing import ConnectionClosed


def wait_for(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_client_connects_and_gets_pong(connect):
    client = connect()
    seq = client.request("PING")
    assert client.recv() == {"type": "PONG", "ref_seq": seq}


def test_two_clients_are_served_independently(connect):
    a, b = connect(), connect()
    seq_a = a.request("PING")
    seq_b = b.request("PING")
    assert b.recv()["ref_seq"] == seq_b
    assert a.recv()["ref_seq"] == seq_a


def test_disconnect_does_not_affect_other_clients(make_server, connect):
    server, _ = make_server()
    a = connect(server.connections.address)
    b = connect(server.connections.address)
    a.request("PING")
    a.recv()
    assert wait_for(lambda: server.connections.connection_count() == 2)

    # Abrupt disconnect in the middle of a frame header.
    a.sock.sendall(b"\x00\x00")
    a.close()

    assert wait_for(lambda: server.connections.connection_count() == 1)
    seq = b.request("PING")
    assert b.recv()["ref_seq"] == seq


def test_connection_cap_returns_server_busy(make_server, connect):
    server, address = make_server(max_connections=1)
    first = connect(address)
    first.request("PING")
    first.recv()

    second = connect(address)
    reply = second.recv()
    assert reply["type"] == "ERROR" and reply["code"] == "SERVER_BUSY"
    with pytest.raises((ConnectionClosed, ConnectionError)):
        second.recv()

    # Once the first client leaves, a new one is accepted.
    first.close()
    assert wait_for(lambda: server.connections.connection_count() == 0)
    third = connect(address)
    seq = third.request("PING")
    assert third.recv()["ref_seq"] == seq


def test_unsupported_message_gets_error(connect):
    client = connect()
    seq = client.request("NOT_A_TYPE")
    reply = client.recv()
    assert reply["type"] == "ERROR" and reply["ref_seq"] == seq


def test_client_network_handler_round_trip(server_address):
    events = queue.Queue()
    conn = ChatConnection(events)
    conn.connect(*server_address)
    seq = conn.request("PING")
    kind, message, request_type = events.get(timeout=5)
    assert kind == "message"
    assert message == {"type": "PONG", "ref_seq": seq}
    assert request_type == "PING"
    conn.close()
    assert events.get(timeout=5) == ("disconnected", "connection closed")


def test_client_reports_lost_connection(make_server):
    server, address = make_server()
    events = queue.Queue()
    conn = ChatConnection(events)
    conn.connect(*address)
    server.stop()
    kind, reason = events.get(timeout=5)
    assert kind == "disconnected"
    assert not conn.connected


def test_client_reports_unreachable_server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # nothing is listening once this socket closes
    with pytest.raises(OSError):
        ChatConnection(queue.Queue()).connect("127.0.0.1", port, timeout=2)
