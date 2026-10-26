"""Client network handler: connects, sends requests, reads replies in the background, sends heartbeats.

Everything received is put on an event queue for the UI to drain on its own thread:
    ("message", message, request_type)   request_type is the type of the request an ACK/ERROR answers
    ("disconnected", reason)
"""
import itertools
import socket
import threading

from server.protocol.framing import ConnectionClosed, FrameError, encode, read_frame

# Larger than the server's 8 KB request limit: server events wrap the text in extra fields.
MAX_INCOMING_FRAME = 64 * 1024


class ChatConnection:
    def __init__(self, events, heartbeat_seconds=30):
        self.events = events
        self.heartbeat_seconds = heartbeat_seconds
        self.session = None
        self._sock = None
        self._send_lock = threading.Lock()
        self._seq = itertools.count(1)
        self._pending = {}
        self._closed = threading.Event()

    @property
    def connected(self):
        return self._sock is not None and not self._closed.is_set()

    def connect(self, host, port, timeout=5):
        """Open the TCP connection. Raises OSError if the server cannot be reached."""
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(None)
        self._sock = sock
        self._closed.clear()
        threading.Thread(target=self._read_loop, name="client-reader", daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, name="client-heartbeat", daemon=True).start()

    def request(self, message_type, payload=None):
        """Send a request and return its sequence number. Raises OSError if the connection is gone."""
        if not self.connected:
            raise OSError("not connected")
        with self._send_lock:
            seq = next(self._seq)
            message = {"type": message_type, "seq": seq, "payload": payload or {}}
            if self.session:
                message["session"] = self.session
            self._pending[seq] = message_type
            self._sock.sendall(encode(message))
        return seq

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        self.session = None
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()

    def _read_loop(self):
        reason = "connection closed"
        try:
            while True:
                message = read_frame(self._sock, MAX_INCOMING_FRAME)
                request_type = self._pending.pop(message.get("ref_seq"), None)
                self.events.put(("message", message, request_type))
        except ConnectionClosed:
            reason = "server closed the connection"
        except FrameError as e:
            reason = f"bad data from server: {e}"
        except OSError as e:
            reason = "connection closed" if self._closed.is_set() else f"connection lost: {e}"
        finally:
            was_open = not self._closed.is_set()
            self.close()
            self.events.put(("disconnected", reason if was_open else "connection closed"))

    def _heartbeat_loop(self):
        while not self._closed.wait(self.heartbeat_seconds):
            try:
                self.request("PING")
            except OSError:
                return
