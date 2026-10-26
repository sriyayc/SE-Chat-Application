"""Issue #4: request validation and the pre-login whitelist (CHAT-F-002, CHAT-F-009, CHAT-SR-004)."""
import pytest

from server.protocol.validator import ValidationError, validate

MAX_TEXT = 2000


def check(message, authenticated=True):
    return validate(message, authenticated, MAX_TEXT)


def rejected(message, authenticated=True):
    with pytest.raises(ValidationError) as info:
        check(message, authenticated)
    return info.value


def msg(**payload):
    return {"type": "MSG", "seq": 1, "session": "token", "payload": payload}


def test_valid_message_is_returned_as_request():
    request = check(msg(to="bob_1", text="hi"))
    assert request.type == "MSG"
    assert request.seq == 1
    assert request.payload == {"to": "bob_1", "text": "hi"}
    assert request.session == "token"


def test_payload_defaults_to_empty():
    assert check({"type": "PING", "seq": 0}, authenticated=False).payload == {}


@pytest.mark.parametrize("seq", [None, -1, "1", 1.5, True])
def test_seq_must_be_non_negative_int(seq):
    message = {"type": "PING", "payload": {}}
    if seq is not None:
        message["seq"] = seq
    error = rejected(message)
    assert error.code == "INVALID_MESSAGE"
    assert error.ref_seq is None


def test_error_echoes_seq_when_it_is_valid():
    assert rejected({"type": "NOPE", "seq": 7}).ref_seq == 7


@pytest.mark.parametrize("message", [
    {"type": "NOPE", "seq": 1},
    {"type": "ping", "seq": 1},
    {"seq": 1},
    {"type": "PING", "seq": 1, "payload": []},
    {"type": "PING", "seq": 1, "extra": 1},
    {"type": "PING", "seq": 1, "payload": {"unexpected": 1}},
    {"type": "PING", "seq": 1, "session": 123},
])
def test_structural_errors(message):
    assert rejected(message).code == "INVALID_MESSAGE"


@pytest.mark.parametrize("message_type", ["MSG", "CREATE_ROOM", "JOIN", "HISTORY", "LOGOUT", "ADMIN"])
def test_only_register_login_ping_before_login(message_type):
    error = rejected({"type": message_type, "seq": 1}, authenticated=False)
    assert error.code == "SESSION_EXPIRED"


@pytest.mark.parametrize("message_type", ["REGISTER", "LOGIN"])
def test_register_and_login_allowed_before_login(message_type):
    message = {"type": message_type, "seq": 1, "payload": {"username": "alice", "password": "password1"}}
    assert check(message, authenticated=False).type == message_type


@pytest.mark.parametrize("username", ["ab", "a" * 33, "has space", "semi;colon", "", 42, None])
def test_bad_usernames(username):
    message = {"type": "LOGIN", "seq": 1, "payload": {"username": username, "password": "x"}}
    assert rejected(message, authenticated=False).code == "INVALID_MESSAGE"


def test_register_password_length():
    def register(password):
        return {"type": "REGISTER", "seq": 1, "payload": {"username": "alice", "password": password}}
    assert rejected(register("short"), authenticated=False)
    assert rejected(register("x" * 129), authenticated=False)
    assert check(register("x" * 8), authenticated=False)


def test_login_does_not_reveal_password_rules():
    # Any non-empty password is accepted for LOGIN so the server, not the validator, decides.
    message = {"type": "LOGIN", "seq": 1, "payload": {"username": "alice", "password": "x"}}
    assert check(message, authenticated=False)


@pytest.mark.parametrize("payload", [
    {"text": "hi"},                               # no target
    {"to": "bob", "room": "general", "text": "hi"},  # two targets
    {"to": "bob"},                                # no text
    {"to": "bob", "text": ""},
    {"to": "bob", "text": "   \n "},
    {"to": "bob", "text": 5},
    {"to": "bob", "text": "x" * (MAX_TEXT + 1)},
    {"room": " padded", "text": "hi"},
    {"room": "x" * 33, "text": "hi"},
])
def test_bad_chat_messages(payload):
    assert rejected(msg(**payload)).code == "INVALID_MESSAGE"


def test_text_at_limit_is_accepted():
    assert check(msg(room="general", text="x" * MAX_TEXT))


@pytest.mark.parametrize("payload, ok", [
    ({"room": "general"}, True),
    ({"with": "bob", "limit": 50, "before_ts": 1700000000.5}, True),
    ({"room": "general", "with": "bob"}, False),
    ({"room": "general", "limit": 0}, False),
    ({"room": "general", "limit": 101}, False),
    ({"room": "general", "before_ts": -1}, False),
    ({"room": "general", "before_ts": True}, False),
])
def test_history_fields(payload, ok):
    message = {"type": "HISTORY", "seq": 1, "payload": payload}
    if ok:
        assert check(message)
    else:
        rejected(message)


def test_admin_fields():
    assert check({"type": "ADMIN", "seq": 1, "payload": {"action": "restrict", "target": "bob"}})
    rejected({"type": "ADMIN", "seq": 1, "payload": {"action": "restrict"}})
    rejected({"type": "ADMIN", "seq": 1, "payload": {"action": "x", "target": "bob", "args": []}})


def test_server_returns_validation_errors(connect):
    client = connect()
    seq = client.request("MSG", {"to": "bob", "text": "hi"})
    reply = client.recv()
    assert reply == {"type": "ERROR", "ref_seq": seq, "code": "SESSION_EXPIRED", "reason": "log in first"}
