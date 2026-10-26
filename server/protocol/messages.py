"""Builders for server-to-client messages and the error codes from the SAD."""

INVALID_MESSAGE = "INVALID_MESSAGE"
AUTH_FAILED = "AUTH_FAILED"
SESSION_EXPIRED = "SESSION_EXPIRED"
FORBIDDEN = "FORBIDDEN"
DUPLICATE = "DUPLICATE"
NOT_FOUND = "NOT_FOUND"
SERVER_BUSY = "SERVER_BUSY"


def ack(ref_seq, status="OK", data=None):
    return {"type": "ACK", "ref_seq": ref_seq, "status": status, "data": data or {}}


def error(ref_seq, code, reason):
    return {"type": "ERROR", "ref_seq": ref_seq, "code": code, "reason": reason}


def event(kind, data):
    return {"type": "EVENT", "kind": kind, "data": data}


def pong(ref_seq):
    return {"type": "PONG", "ref_seq": ref_seq}
