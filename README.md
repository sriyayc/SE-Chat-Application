# Chat Application using Socket Programming

A Python desktop chat application with a Tkinter client and a threaded TCP server. Client/server
traffic uses TLS and length-prefixed JSON frames. The server provides registration and login,
presence, direct and room messaging, persistent history, configurable idle-session expiry, and
administrator controls.

## Requirements

- Python 3.11 or later.
- OpenSSL for generating a local development TLS certificate, unless you already have a
  certificate and its matching private key.
- A graphical desktop session to run the Tkinter client. On some Linux distributions, Tkinter
  must be installed separately (for example, `python3-tk`).

The only Python package in `requirements.txt` is `pytest`; application code otherwise uses the
Python standard library.

## Installation

Run commands from the repository root.

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, allow scripts for the current process with
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate the environment.
Use `py -3.12` (or another installed Python 3.11+) if that is the interpreter you have.

### Linux or macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## TLS certificate setup

The server requires a certificate and its matching private key. The client verifies the server
certificate using `certs/server.crt`; the server reads the certificate and key paths from its
configuration. The private key is deliberately not included in the repository.

For local development, create a self-signed certificate with a Subject Alternative Name matching
the address clients use. This example replaces `certs/server.crt` in your working copy and creates
the ignored private key:

```sh
openssl req -x509 -newkey rsa:2048 -keyout certs/server.key -out certs/server.crt \
  -days 365 -nodes -subj "/CN=127.0.0.1" \
  -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

Use a certificate with the correct DNS/IP Subject Alternative Name for any non-local server.
Do not commit the private key or local certificate changes. For production, provision certificates
and keys securely; do not use a self-signed development certificate as a production deployment
policy.

## Configuration

The server loads defaults from `server/config.py`. It optionally reads `config.json` in the
repository root; alternatively, pass a JSON file with `--config PATH`. Start from the template:

```powershell
Copy-Item config.example.json config.json
```

```sh
cp config.example.json config.json
```

Unknown keys and invalid values are rejected. Relative file paths resolve from the repository
root, regardless of the current directory.

| Setting | Default | Description |
|---|---:|---|
| `host` | `0.0.0.0` | Server listen address. |
| `port` | `5050` | Server listen port; `0` selects an available port in tests. |
| `max_frame_bytes` | `8192` | Maximum client request frame body, in bytes. |
| `max_text_chars` | `2000` | Maximum chat message text length. |
| `max_connections` | `100` | Maximum simultaneous client connections. |
| `max_rooms` | `50` | Maximum number of non-removed rooms. |
| `idle_timeout_seconds` | `900` | Inactivity period before a session expires. |
| `heartbeat_seconds` | `30` | Client heartbeat interval; also controls the server read timeout. |
| `tls_cert_path` | `certs/server.crt` | Server certificate path. The client separately uses its fixed `certs/server.crt` trust-file path. |
| `tls_key_path` | `certs/server.key` | Server private key (keep secret; do not commit). |
| `db_path` | `data/chat.db` | SQLite database path. |
| `log_path` | `logs/server.log` | Rotating server log path. |

The server enforces TLS 1.2 or newer. The client currently uses `certs/server.crt` as its
certificate trust file; changing the certificate path requires changing the client connection
setup as well as the server configuration.

## Run the application

Start the server in one terminal:

```sh
python -m server.main
```

Start a client in another terminal:

```sh
python -m client.main
```

The client defaults to `127.0.0.1:5050`. To connect to another server:

```sh
python -m client.main --host 192.168.1.20 --port 5050
```

The server can also be started with an alternate configuration or listen address:

```sh
python -m server.main --config path/to/config.json
python -m server.main --host 127.0.0.1 --port 5050
```

Press `Ctrl+C` in the server terminal to stop it cleanly.

## Implemented architecture

1. `client/ui` provides the Tkinter login and chat interface. UI work stays on Tk's main thread;
   background connection and reader threads deliver events through a queue.
2. `client/net` establishes the TLS connection, sends requests, reads server frames, and sends
   heartbeats.
3. `server/transport` accepts TLS connections and runs a reader and writer thread per connection.
   Each client has a bounded outbound queue so frames from concurrent senders do not interleave.
4. `server/protocol` decodes length-prefixed JSON, validates request shape and values, dispatches
   requests, and builds replies and events.
5. `server/services` implements authentication, sessions, presence, room membership, message
   routing/history, and administrative actions.
6. `server/persistence` owns SQLite schema and access. Chat messages and audit records are queued
   to a database writer thread; other database operations are serialized with a lock.
7. `server/audit` records security/admin events and redacts passwords and session tokens from
   application logs.

The architecture and requirement-to-code/test links are documented in
[documents/requirements-traceability.md](documents/requirements-traceability.md). The submitted
specifications and diagrams are under `documents/`; implementation differences are tracked in
[documents/implementation-notes.md](documents/implementation-notes.md).

## Features and administration

- Register and log in; usernames are case-insensitive and only one active login per account is
  allowed.
- Send direct messages or create, join, leave, and message rooms.
- View saved conversation history. Offline messages are saved for later history retrieval; they
  are not pushed to clients while offline.
- Use administrator commands in the client's message box. Type `/admin` to display help. Examples:
  `/admin deactivate bob`, `/admin restrict_room general`,
  `/admin rename_room general lobby`.
- Grant or remove the administrator role from the server machine, using the configured database:

```sh
python -m server.manage make-admin alice
python -m server.manage remove-admin alice
python -m server.manage audit --limit 50
```

Role changes take effect at the account's next login. An administrator cannot change their own
account through the client.

## Tests and verification

Run the automated suite from the repository root:

```sh
python -m pytest -v
```

The tests use a short-lived self-signed TLS certificate. CI generates a test certificate/key pair
before running pytest. Locally, provide a matching `certs/server.crt` and `certs/server.key` pair
before running network tests. Tkinter UI tests require a display and are skipped in headless
environments.

The latest recorded local run and the current requirement coverage are in
[documents/issue-15-qa-validation.md](documents/issue-15-qa-validation.md) and
[documents/requirements-traceability.md](documents/requirements-traceability.md).

## Known limitations

- This is a single-server application; clustering and high availability are not implemented.
- Chat history is stored in SQLite without application-level encryption at rest. TLS protects
  traffic in transit; it does not provide end-to-end encryption.
- Local self-signed certificates are for development/testing only. Production certificate
  provisioning, rotation, and operational hardening remain deployment responsibilities.
- The client's certificate trust path is fixed in the client code and currently defaults to
  `certs/server.crt`.
- Automated UI tests need a graphical display. Session idle-expiry behavior is implemented but
  does not yet have a dedicated expiry-focused automated test.
- Message persistence is asynchronous. A database write failure is logged and does not stop the
  server, but a message may fail to persist after it has already been delivered.
