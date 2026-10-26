"""Message type, field and length checks; pre-login whitelist (CHAT-F-009, CHAT-SR-004).

Every request is checked here before any service sees it. The schema is strict:
unknown message types, unknown fields, wrong types and out-of-range values are all
rejected, so services can trust the fields they receive.
"""
import re
from typing import NamedTuple

from server.protocol import messages

USERNAME_RE = re.compile(r"[A-Za-z0-9_.-]{3,32}")
ROOM_RE = re.compile(r"[A-Za-z0-9_.-][A-Za-z0-9 _.-]{0,31}")
PASSWORD_MIN, PASSWORD_MAX = 8, 128
HISTORY_LIMIT_MAX = 100

PRE_LOGIN_TYPES = frozenset({"REGISTER", "LOGIN", "PING"})
TOP_LEVEL_FIELDS = frozenset({"type", "seq", "payload", "session"})


class ValidationError(Exception):
    def __init__(self, code, reason, ref_seq=None):
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.ref_seq = ref_seq


class Request(NamedTuple):
    type: str
    seq: int
    payload: dict
    session: str | None


def validate(message, authenticated, max_text_chars):
    """Return a Request or raise ValidationError carrying the error code to send back."""
    seq = message.get("seq")
    ref_seq = seq if _is_int(seq) and seq >= 0 else None

    def fail(reason, code=messages.INVALID_MESSAGE):
        raise ValidationError(code, reason, ref_seq)

    if ref_seq is None:
        fail("seq must be a non-negative integer")
    extra = set(message) - TOP_LEVEL_FIELDS
    if extra:
        fail(f"unexpected field(s): {', '.join(sorted(extra))}")
    message_type = message.get("type")
    if message_type not in SCHEMAS:
        fail("unknown message type")
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        fail("payload must be an object")
    session = message.get("session")
    if session is not None and not isinstance(session, str):
        fail("session must be a string")
    if not authenticated and message_type not in PRE_LOGIN_TYPES:
        fail("log in first", messages.SESSION_EXPIRED)

    try:
        SCHEMAS[message_type](payload, max_text_chars)
    except _FieldError as e:
        fail(str(e))
    return Request(message_type, seq, payload, session)


class _FieldError(Exception):
    pass


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _fields(payload, required=(), optional=()):
    unknown = set(payload) - set(required) - set(optional)
    if unknown:
        raise _FieldError(f"unexpected field(s): {', '.join(sorted(unknown))}")
    missing = [name for name in required if name not in payload]
    if missing:
        raise _FieldError(f"missing field(s): {', '.join(missing)}")


def _one_of(payload, a, b):
    if (a in payload) == (b in payload):
        raise _FieldError(f"exactly one of '{a}' or '{b}' is required")
    return a if a in payload else b


def _username(value, field="username"):
    if not isinstance(value, str) or not USERNAME_RE.fullmatch(value):
        raise _FieldError(f"{field} must be 3-32 letters, digits, '_', '.' or '-'")


def _room(value):
    if not isinstance(value, str) or not ROOM_RE.fullmatch(value) or value != value.strip():
        raise _FieldError("room must be 1-32 letters, digits, spaces, '_', '.' or '-'")


def _password(value, min_length):
    if not isinstance(value, str) or not min_length <= len(value) <= PASSWORD_MAX:
        raise _FieldError(f"password must be {min_length}-{PASSWORD_MAX} characters")


def _text(value, max_chars):
    if not isinstance(value, str) or not value.strip():
        raise _FieldError("text must be a non-empty string")
    if len(value) > max_chars:
        raise _FieldError(f"text is longer than {max_chars} characters")


def _register(p, _):
    _fields(p, required=("username", "password"))
    _username(p["username"])
    _password(p["password"], PASSWORD_MIN)


def _login(p, _):
    _fields(p, required=("username", "password"))
    _username(p["username"])
    _password(p["password"], 1)


def _room_only(p, _):
    _fields(p, required=("room",))
    _room(p["room"])


def _msg(p, max_text_chars):
    _fields(p, required=("text",), optional=("room", "to"))
    if _one_of(p, "room", "to") == "room":
        _room(p["room"])
    else:
        _username(p["to"], "to")
    _text(p["text"], max_text_chars)


def _history(p, _):
    _fields(p, optional=("room", "with", "before_ts", "limit"))
    if _one_of(p, "room", "with") == "room":
        _room(p["room"])
    else:
        _username(p["with"], "with")
    before = p.get("before_ts")
    if before is not None and (isinstance(before, bool) or not isinstance(before, (int, float)) or before < 0):
        raise _FieldError("before_ts must be a non-negative number")
    limit = p.get("limit")
    if limit is not None and (not _is_int(limit) or not 1 <= limit <= HISTORY_LIMIT_MAX):
        raise _FieldError(f"limit must be an integer from 1 to {HISTORY_LIMIT_MAX}")


def _admin(p, _):
    _fields(p, required=("action", "target"), optional=("args",))
    for name, max_len in (("action", 32), ("target", 64)):
        if not isinstance(p[name], str) or not 1 <= len(p[name]) <= max_len:
            raise _FieldError(f"{name} must be a string of 1-{max_len} characters")
    if "args" in p and not isinstance(p["args"], dict):
        raise _FieldError("args must be an object")


def _empty(p, _):
    _fields(p)


SCHEMAS = {
    "REGISTER": _register,
    "LOGIN": _login,
    "CREATE_ROOM": _room_only,
    "JOIN": _room_only,
    "LEAVE": _room_only,
    "MSG": _msg,
    "HISTORY": _history,
    "ADMIN": _admin,
    "LOGOUT": _empty,
    "PING": _empty,
}
