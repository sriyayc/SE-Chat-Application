"""Passes each decoded request to the service that handles it."""
from server.protocol import messages


class Dispatcher:
    def __init__(self, config):
        self.config = config

    def handle(self, conn, message):
        seq = message.get("seq")
        if message.get("type") == "PING":
            conn.send(messages.pong(seq))
            return
        conn.send(messages.error(seq, messages.INVALID_MESSAGE, "unsupported message type"))

    def disconnected(self, conn):
        pass
