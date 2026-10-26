"""Validates each decoded request and passes it to the service that handles it."""
import logging

from server.protocol import messages
from server.protocol.validator import ValidationError, validate

log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, config):
        self.max_text_chars = config["max_text_chars"]
        self._handlers = {
            "PING": self._ping,
        }

    def handle(self, conn, message):
        try:
            request = validate(message, conn.authenticated, self.max_text_chars)
        except ValidationError as e:
            # Only the reason is logged, never the request itself: it may contain a password.
            log.warning("%r request rejected (%s): %s", conn, e.code, e.reason)
            conn.send(messages.error(e.ref_seq, e.code, e.reason))
            return
        handler = self._handlers.get(request.type)
        if handler is None:
            conn.send(messages.error(request.seq, messages.INVALID_MESSAGE, f"{request.type} is not supported yet"))
            return
        handler(conn, request)

    def disconnected(self, conn):
        pass

    def _ping(self, conn, request):
        conn.send(messages.pong(request.seq))
