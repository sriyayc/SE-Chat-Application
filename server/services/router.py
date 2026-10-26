"""Message delivery, ordering, delivery status, history.

A message is put straight onto the recipient's outbound queue. Each connection is
read by one thread and written by one thread, so messages from one sender reach a
recipient in the order they were sent (CHAT-F-008). Room delivery comes with #8 and
storing messages for history with #9.
"""
import logging
import time

from server.protocol import messages

log = logging.getLogger(__name__)


class Router:
    def __init__(self, presence, repo):
        self.presence = presence
        self.repo = repo

    def route(self, sender, request):
        """Deliver a validated MSG request and return the ACK or ERROR for the sender."""
        payload = request.payload
        if "room" in payload:
            return messages.error(request.seq, messages.NOT_FOUND, "chat rooms are not available yet")
        to = payload["to"]
        sender_name = sender.user["username"]
        if to.casefold() == sender_name.casefold():
            return messages.error(request.seq, messages.INVALID_MESSAGE, "you cannot message yourself")

        ts = time.time()
        recipient = self.presence.get(to)
        if recipient is None:
            if self.repo.get_user(to) is None:
                return messages.error(request.seq, messages.NOT_FOUND, f"there is no user called {to}")
            return self._not_delivered(request.seq, to, ts)

        recipient_name = recipient.user["username"]
        delivered = recipient.send(messages.event("msg", {
            "from": sender_name, "to": recipient_name, "seq": request.seq, "text": payload["text"], "ts": ts}))
        if not delivered:
            return self._not_delivered(request.seq, recipient_name, ts)
        return messages.ack(request.seq, "DELIVERED", {"to": recipient_name, "ts": ts})

    @staticmethod
    def _not_delivered(seq, to, ts):
        # CHAT-F-010: tell the sender the recipient is unavailable.
        return messages.ack(seq, "NOT_DELIVERED", {"to": to, "ts": ts, "reason": f"{to} is offline"})
