-- Tables: User, ChatRoom, RoomMember, Message, Session, AuditLog (see SAD)
-- ChatRoom, RoomMember, Message and AuditLog are added with rooms (#8), history (#9) and audit logging (#10).

CREATE TABLE IF NOT EXISTS User (
    UserID       INTEGER PRIMARY KEY AUTOINCREMENT,
    Username     TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    PasswordHash BLOB    NOT NULL,
    Salt         BLOB    NOT NULL,
    Role         TEXT    NOT NULL DEFAULT 'USER'   CHECK (Role IN ('USER', 'ADMIN')),
    Status       TEXT    NOT NULL DEFAULT 'ACTIVE' CHECK (Status IN ('ACTIVE', 'RESTRICTED', 'DEACTIVATED')),
    CreatedAt    TEXT    NOT NULL
);

-- Only a hash of the session token is stored.
CREATE TABLE IF NOT EXISTS Session (
    SessionID      INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID         INTEGER NOT NULL REFERENCES User(UserID),
    TokenHash      TEXT    NOT NULL UNIQUE,
    ConnectedAt    TEXT    NOT NULL,
    LastActivity   TEXT    NOT NULL,
    DisconnectedAt TEXT
);

CREATE INDEX IF NOT EXISTS idx_session_user ON Session(UserID);
