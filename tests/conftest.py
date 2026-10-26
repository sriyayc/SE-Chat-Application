import socket

import pytest

from server.app import ChatServer
from server.config import load_config
from server.protocol.framing import encode, read_frame


class RawClient:
    """A bare socket client that speaks the frame protocol, for driving the server in tests."""

    def __init__(self, address, timeout=5):
        self.sock = socket.create_connection(address, timeout=timeout)
        self._seq = 0
        self.session = None

    def send(self, message):
        self.sock.sendall(encode(message))

    def request(self, message_type, payload=None, **extra):
        self._seq += 1
        message = {"type": message_type, "seq": self._seq, "payload": payload or {}}
        if self.session:
            message["session"] = self.session
        message.update(extra)
        self.send(message)
        return self._seq

    def recv(self):
        return read_frame(self.sock, 1 << 20)

    def reply_to(self, seq):
        """Read until the ACK/ERROR for `seq` arrives, skipping events."""
        while True:
            message = self.recv()
            if message.get("ref_seq") == seq:
                return message

    def close(self):
        self.sock.close()


@pytest.fixture
def make_server(tmp_path):
    servers = []

    def start(**overrides):
        settings = {
            "host": "127.0.0.1",
            "port": 0,
            "db_path": str(tmp_path / "chat.db"),
            "log_path": str(tmp_path / "server.log"),
        }
        settings.update(overrides)
        # An empty file, so a developer's own config.json never changes test behaviour.
        empty = tmp_path / "config.json"
        empty.write_text("{}", encoding="utf-8")
        server = ChatServer(load_config(empty, **settings))
        address = server.start()
        servers.append(server)
        return server, address

    yield start
    for server in servers:
        server.stop()


@pytest.fixture
def server_address(make_server):
    return make_server()[1]


@pytest.fixture
def connect(server_address):
    clients = []

    def open_client(address=server_address):
        client = RawClient(address)
        clients.append(client)
        return client

    yield open_client
    for client in clients:
        client.close()
