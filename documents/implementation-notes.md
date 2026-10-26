# Implementation Notes and Deviations from the SAD

The SAD, Mini-Project Part-2 and the role-based task division ask for any difference between the
implementation and the submitted documents to be written down and explained at the final demo.
This file tracks those differences. Update it whenever the code and the SAD disagree.

## Sprint 1 (issues #1-#6)

### Planned for later sprints (not deviations, just not built yet)
| SAD item | Status | Issue |
|---|---|---|
| TLS 1.2+ with a pinned server certificate | Plain TCP for now. All framing and validation is already in place on top of the socket. | #11 |
| Session idle timeout and sweeper | The token is checked on every request; idle expiry is not enforced yet. | #11 |
| Chat rooms, presence events, join/leave notifications | MSG supports `to` (direct messages). `room` is validated but answered with `NOT_FOUND` until rooms exist. | #8 |
| Message persistence and history | Messages are delivered but not stored. | #9 |
| Admin service and audit log with redaction | Security events go to the rotating server log; passwords and tokens are never written. | #10 |

### Differences from the SAD
| # | SAD says | Implementation | Why |
|---|---|---|---|
| D1 | Offline recipient: `ACK {status: STORED_NOT_DELIVERED}` | `ACK {status: NOT_DELIVERED, data: {reason}}` | Nothing is stored until #9; the status will become `STORED_NOT_DELIVERED` then. |
| D2 | Oversized frame: rejected before reading the body | Still rejected from the length prefix alone. Bodies up to 1 MB are then skipped (not buffered) so the client can carry on; larger ones get `INVALID_MESSAGE` and the connection is closed. | Without skipping or closing, the TCP stream would be out of sync after the rejection. |
| D3 | Data Repository: all writes through one writer thread | One lock serialises all database access (still a single writer). | Only user and session writes exist so far; the dedicated writer thread for messages comes with #9. |
| D4 | Module layout lists components only | Added `server/app.py` (wires the layers), `server/config.py` (settings), `server/protocol/dispatcher.py` (passes validated requests to services), `server/protocol/messages.py` (ACK/ERROR/EVENT builders and error codes). | Keeps each SAD component in its own module; no new responsibilities. |
| D5 | Client Network Handler packs/unpacks messages | The client reuses `server/protocol/framing.py` instead of a copy. | One implementation of the wire format for both sides. |
| D6 | Not specified | Usernames are unique ignoring case (`Alice` and `alice` are the same account); the stored spelling is shown. | Prevents look-alike accounts. |
| D7 | Not specified | One active login per account; a second login gets `FORBIDDEN`. | Direct messages are routed by username, so one connection per user keeps delivery unambiguous. |
| D8 | Not specified | Usernames: 3-32 of `A-Z a-z 0-9 _ . -`; passwords 8-128 characters at registration; room names 1-32 of letters, digits, spaces, `_ . -`. | The SRS asks for "valid account information" without defining it. |
| D9 | Error codes table | `REGISTER`/`LOGIN` while already logged in returns `FORBIDDEN`. | Uses an existing code; no new codes were added. |

## Protocol summary (as implemented)
Every frame is a 4-byte big-endian length followed by a UTF-8 JSON object, at most `max_frame_bytes`.

Client requests: `{"type", "seq", "payload", "session"}`. `session` is required after login.

| Request | Payload | Success reply |
|---|---|---|
| `REGISTER` | `username`, `password` | `ACK REGISTERED` |
| `LOGIN` | `username`, `password` | `ACK LOGGED_IN {session, username, role}` |
| `MSG` | `to`, `text` | `ACK DELIVERED {to, ts}` or `ACK NOT_DELIVERED {to, ts, reason}` |
| `LOGOUT` | none | `ACK LOGGED_OUT`, then the server closes the connection |
| `PING` | none | `PONG` |

The recipient gets `EVENT {kind: "msg", data: {from, to, seq, text, ts}}`.
Errors are `ERROR {ref_seq, code, reason}` with the codes from the SAD.
