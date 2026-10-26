"""Issue #3: registration and authentication (CHAT-F-001, CHAT-F-002, CHAT-SR-002; TC-REG-01, TC-AUTH-01, TC-SEC-03)."""
import logging
import queue
import sqlite3

from client.net.connection import ChatConnection

PASSWORD = "correct horse battery"


def register(client, username, password=PASSWORD):
    return client.reply_to(client.request("REGISTER", {"username": username, "password": password}))


def login(client, username, password=PASSWORD):
    reply = client.reply_to(client.request("LOGIN", {"username": username, "password": password}))
    if reply["type"] == "ACK":
        client.session = reply["data"]["session"]
    return reply


def test_register_then_login(connect):
    client = connect()
    assert register(client, "alice") == {"type": "ACK", "ref_seq": 1, "status": "REGISTERED", "data": {}}
    reply = login(client, "alice")
    assert reply["status"] == "LOGGED_IN"
    assert reply["data"]["username"] == "alice"
    assert reply["data"]["role"] == "USER"
    assert len(reply["data"]["session"]) >= 32


def test_duplicate_username_rejected_case_insensitively(connect):
    client = connect()
    register(client, "alice")
    for name in ("alice", "ALICE"):
        reply = register(client, name)
        assert reply["type"] == "ERROR" and reply["code"] == "DUPLICATE"


def test_wrong_password_and_unknown_user_look_the_same(connect):
    client = connect()
    register(client, "alice")
    wrong = login(client, "alice", "not the password")
    unknown = login(client, "nobody", PASSWORD)
    assert wrong["code"] == unknown["code"] == "AUTH_FAILED"
    assert wrong["reason"] == unknown["reason"]


def test_restricted_account_gets_same_error(make_server, connect):
    server, address = make_server()
    client = connect(address)
    register(client, "alice")
    with server.repo._lock:
        server.repo._db.execute("UPDATE User SET Status = 'RESTRICTED' WHERE Username = 'alice'")
    assert login(client, "alice")["code"] == "AUTH_FAILED"


def test_login_is_case_insensitive_but_returns_stored_name(connect):
    client = connect()
    register(client, "Alice")
    assert login(client, "alice")["data"]["username"] == "Alice"


def test_protected_requests_need_login(connect):
    client = connect()
    reply = client.reply_to(client.request("LOGOUT"))
    assert reply["code"] == "SESSION_EXPIRED"


def test_requests_need_the_right_session_token(connect):
    client = connect()
    register(client, "alice")
    login(client, "alice")
    client.session = "forged-token"
    assert client.reply_to(client.request("LOGOUT"))["code"] == "SESSION_EXPIRED"
    client.session = None
    assert client.reply_to(client.request("LOGOUT"))["code"] == "SESSION_EXPIRED"


def test_cannot_log_in_twice(connect):
    first, second = connect(), connect()
    register(first, "alice")
    login(first, "alice")
    assert login(first, "alice")["code"] == "FORBIDDEN"
    assert login(second, "alice")["code"] == "FORBIDDEN"


def test_can_log_in_again_after_disconnect(make_server, connect):
    server, address = make_server()
    first = connect(address)
    register(first, "alice")
    login(first, "alice")
    first.close()
    second = connect(address)
    for _ in range(50):
        reply = login(second, "alice")
        if reply["type"] == "ACK":
            break
    assert reply["status"] == "LOGGED_IN"


def test_logout_ends_session_and_closes_connection(make_server, connect):
    server, address = make_server()
    client = connect(address)
    register(client, "alice")
    login(client, "alice")
    assert client.reply_to(client.request("LOGOUT"))["status"] == "LOGGED_OUT"
    assert client.sock.recv(1) == b""
    with sqlite3.connect(server.config["db_path"]) as db:
        assert db.execute("SELECT COUNT(*) FROM Session WHERE DisconnectedAt IS NULL").fetchone()[0] == 0


def test_no_plaintext_passwords_or_tokens_stored(make_server, connect):
    server, address = make_server()
    client = connect(address)
    register(client, "alice")
    token = login(client, "alice")["data"]["session"]
    with sqlite3.connect(server.config["db_path"]) as db:
        dump = "\n".join(db.iterdump())
        salt, digest = db.execute("SELECT Salt, PasswordHash FROM User").fetchone()
    assert PASSWORD not in dump
    assert PASSWORD.encode().hex() not in dump.lower()
    assert token not in dump
    assert len(salt) == 16 and len(digest) == 64


def test_passwords_never_logged(connect, caplog):
    caplog.set_level(logging.DEBUG)
    client = connect()
    register(client, "alice")
    login(client, "alice", "wrong password 123")
    login(client, "alice")
    client.reply_to(client.request("REGISTER", {"username": "x", "password": "short pw"}))
    assert "login failed for 'alice': wrong password" in caplog.text
    for secret in (PASSWORD, "wrong password 123", "short pw"):
        assert secret not in caplog.text


def test_client_handler_stores_session_token(server_address):
    events = queue.Queue()
    conn = ChatConnection(events)
    conn.connect(*server_address)
    conn.request("REGISTER", {"username": "carol", "password": PASSWORD})
    assert events.get(timeout=5)[1]["status"] == "REGISTERED"
    conn.request("LOGIN", {"username": "carol", "password": PASSWORD})
    _, reply, request_type = events.get(timeout=5)
    assert request_type == "LOGIN"
    assert conn.session == reply["data"]["session"]
    conn.request("LOGOUT")
    assert events.get(timeout=5)[1]["status"] == "LOGGED_OUT"
    conn.close()
