"""Session tokens, last activity, idle-session sweeper.

A session starts on login: the client gets a random token that it must send with
every later request, and only a SHA-256 hash of it is stored. Idle expiry and the
sweeper come with secure session management (#11).
"""
import hashlib
import hmac
import secrets
from typing import NamedTuple


class Session(NamedTuple):
    id: int
    token: str


class SessionService:
    def __init__(self, repo):
        self.repo = repo

    def start(self, user_id):
        token = secrets.token_urlsafe(32)
        session_id = self.repo.create_session(user_id, hashlib.sha256(token.encode()).hexdigest())
        return Session(session_id, token)

    def end(self, session):
        self.repo.end_session(session.id)

    @staticmethod
    def matches(session, presented_token):
        return (session is not None and isinstance(presented_token, str)
                and hmac.compare_digest(session.token.encode(), presented_token.encode()))
