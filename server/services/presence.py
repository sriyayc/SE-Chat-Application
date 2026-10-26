"""Who is online; presence events.

Keeps one connection per logged-in user, keyed case-insensitively to match the
username column. Presence notifications to other users come with #8.
"""
import threading


class Presence:
    def __init__(self):
        self._online = {}
        self._lock = threading.Lock()

    def add(self, username, conn):
        """Register a logged-in connection. Returns False if the user is already online elsewhere."""
        with self._lock:
            key = username.casefold()
            if key in self._online:
                return False
            self._online[key] = conn
            return True

    def remove(self, username, conn):
        with self._lock:
            key = username.casefold()
            if self._online.get(key) is conn:
                del self._online[key]

    def get(self, username):
        with self._lock:
            return self._online.get(username.casefold())

    def online_users(self):
        with self._lock:
            return sorted(conn.user["username"] for conn in self._online.values())
