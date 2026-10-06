# Chat Application using Socket Programming
Software Engineering project: a Python client-server chat app over TLS-encrypted TCP sockets.

## Layout
- `server/transport` - connections and threads
- `server/protocol` - message framing and validation
- `server/services` - auth, sessions, presence, rooms, routing, admin
- `server/persistence` - SQLite access
- `server/audit` - audit log
- `client/ui`, `client/net` - Tkinter client

## Setup
```
python -m venv .venv
pip install -r requirements.txt
cp config.example.json config.json
```
The server certificate goes in `certs/`. The private key is git-ignored and must never be committed.
