"""Accept loop, per-client reader/writer threads, connection cap, cleanup on disconnect.

Each client gets a reader thread (decodes frames and hands them to the dispatcher),
a writer thread and its own outbound queue, so a slow client never holds up anyone
else and frames to one socket never interleave (SAD, Chosen Architecture Pattern).
"""
import itertools
import logging
import queue
import socket
import threading

from server.protocol import messages
from server.protocol.framing import ConnectionClosed, FrameError, FrameTooLarge, discard, encode, read_frame

log = logging.getLogger(__name__)

UNAUTHENTICATED = "UNAUTHENTICATED"
AUTHENTICATED = "AUTHENTICATED"
CLOSING = "CLOSING"

OUTBOUND_QUEUE_SIZE = 1000
# Oversized frames up to this size are skipped so the client can carry on; larger ones close the connection.
DISCARD_LIMIT = 1 << 20
ACCEPT_POLL_SECONDS = 0.5


class ClientConnection:
    _ids = itertools.count(1)

    def __init__(self, sock, addr):
        self.id = next(self._ids)
        self.sock = sock
        self.addr = addr
        self.state = UNAUTHENTICATED
        self.user = None
        self.outbound = queue.Queue(maxsize=OUTBOUND_QUEUE_SIZE)
        self._closed = threading.Event()

    def __repr__(self):
        return f"<conn {self.id} {self.addr[0]}:{self.addr[1]} {self.state}>"

    @property
    def authenticated(self):
        return self.state == AUTHENTICATED

    @property
    def closed(self):
        return self._closed.is_set()

    def send(self, message):
        """Queue a message for the writer thread. Drops the client if it has fallen too far behind."""
        if self.closed:
            return False
        try:
            self.outbound.put_nowait(message)
            return True
        except queue.Full:
            log.warning("%r outbound queue full; dropping client", self)
            self.close()
            return False

    def wait_closed(self, timeout):
        return self._closed.wait(timeout)

    def close_after_flush(self):
        """Close once everything already queued has been sent (e.g. after a final ERROR or ACK)."""
        self.state = CLOSING
        try:
            self.outbound.put_nowait(None)
        except queue.Full:
            self.close()

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        self.state = CLOSING
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


class ConnectionManager:
    def __init__(self, config, on_message, on_disconnect):
        self.host = config["host"]
        self.port = config["port"]
        self.max_connections = config["max_connections"]
        self.max_frame_bytes = config["max_frame_bytes"]
        # Clients ping every heartbeat_seconds, so silence for three intervals means the peer is gone.
        self.read_timeout = config["heartbeat_seconds"] * 3
        self._on_message = on_message
        self._on_disconnect = on_disconnect
        self._connections = {}
        self._lock = threading.Lock()
        self._stopping = threading.Event()
        self._listener = None
        self.address = None
        self.ready = threading.Event()

    def connection_count(self):
        with self._lock:
            return len(self._connections)

    def serve_forever(self):
        self._listener = socket.create_server((self.host, self.port), backlog=128)
        self._listener.settimeout(ACCEPT_POLL_SECONDS)
        self.address = self._listener.getsockname()[:2]
        log.info("listening on %s:%s", *self.address)
        self.ready.set()
        try:
            while not self._stopping.is_set():
                try:
                    sock, addr = self._listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._stopping.is_set():
                        break
                    raise
                self._accept(sock, addr)
        finally:
            self._listener.close()

    def stop(self):
        self._stopping.set()
        with self._lock:
            connections = list(self._connections.values())
        for conn in connections:
            conn.close()

    def _accept(self, sock, addr):
        sock.settimeout(self.read_timeout)
        with self._lock:
            if len(self._connections) >= self.max_connections:
                busy = True
            else:
                busy = False
                conn = ClientConnection(sock, addr)
                self._connections[conn.id] = conn
        if busy:
            log.warning("connection cap %d reached; rejecting %s:%s", self.max_connections, *addr[:2])
            try:
                sock.sendall(encode(messages.error(None, messages.SERVER_BUSY, "server is full, try again later")))
            except OSError:
                pass
            sock.close()
            return
        log.info("%r connected", conn)
        threading.Thread(target=self._reader, args=(conn,), name=f"reader-{conn.id}", daemon=True).start()
        threading.Thread(target=self._writer, args=(conn,), name=f"writer-{conn.id}", daemon=True).start()

    def _reader(self, conn):
        reason = "closed"
        try:
            while not conn.closed:
                try:
                    message = read_frame(conn.sock, self.max_frame_bytes)
                except FrameTooLarge as e:
                    log.warning("%r sent an oversized frame (%d bytes)", conn, e.length)
                    conn.send(messages.error(None, messages.INVALID_MESSAGE, str(e)))
                    if e.length > DISCARD_LIMIT:
                        # Too big to skip: close once the error has been sent.
                        reason = f"oversized frame of {e.length} bytes"
                        conn.close_after_flush()
                        conn.wait_closed(2)
                        return
                    discard(conn.sock, e.length)
                    continue
                except FrameError as e:
                    # The length prefix was honoured, so the stream is still in sync.
                    log.warning("%r sent a malformed frame: %s", conn, e)
                    conn.send(messages.error(None, messages.INVALID_MESSAGE, str(e)))
                    continue
                try:
                    self._on_message(conn, message)
                except Exception:
                    # A bug while handling one request must not take the connection or the server down.
                    log.exception("error handling message from %r", conn)
        except (ConnectionClosed, ConnectionResetError, ConnectionAbortedError):
            reason = "client disconnected"
        except socket.timeout:
            reason = "timed out"
        except OSError as e:
            reason = "closed" if conn.closed else f"socket error: {e}"
        finally:
            self._cleanup(conn, reason)

    def _writer(self, conn):
        while not conn.closed:
            try:
                message = conn.outbound.get(timeout=ACCEPT_POLL_SECONDS)
            except queue.Empty:
                continue
            if message is None:
                break
            try:
                conn.sock.sendall(encode(message))
            except (TypeError, ValueError):
                log.exception("could not encode message for %r", conn)
            except OSError:
                break
        conn.close()

    def _cleanup(self, conn, reason):
        conn.close()
        with self._lock:
            removed = self._connections.pop(conn.id, None) is not None
        if removed:
            log.info("%r disconnected (%s)", conn, reason)
            try:
                self._on_disconnect(conn)
            except Exception:
                log.exception("error cleaning up %r", conn)
