# Requirements Traceability and Verification

This matrix follows the requirement IDs in `SRS.docx`, the component design in `SAD.docx` and
`SAD_T1.docx`, and the test IDs in `se-testplan.docx`. “Automated evidence” names tests in the
repository; STP test IDs are preserved even where the automated suite uses different Python test
names. Issue #12's additional performance/recovery cases are recorded separately in
`issue-12-qa-test-plan.md`.

## Functional requirements

| SRS requirement | SAD design area | Implementation | STP case | Automated evidence | Coverage |
|---|---|---|---|---|---|
| CHAT-F-001 Registration and unique usernames | Auth module | `server/services/auth.py`, `server/protocol/validator.py`, `server/persistence/repository.py` | TC-REG-01 | `tests/test_auth.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |
| CHAT-F-002 Authentication before protected actions | Auth/session modules | `server/services/auth.py`, `server/services/sessions.py`, `server/protocol/dispatcher.py` | TC-AUTH-01 | `tests/test_auth.py`, `tests/test_validator.py` | Implemented and behaviorally tested |
| CHAT-F-003 Client/server socket connection | Socket/connection manager | `client/net/connection.py`, `server/transport/connection_manager.py` | TC-CONN-01 | `tests/test_connection.py` | Implemented and behaviorally tested |
| CHAT-F-004 Connection status and permitted online users | Presence module | `server/services/presence.py`, `client/ui/app.py` | TC-USER-01 | `tests/test_rooms.py`, `tests/test_client_ui.py` | Implemented; UI test requires a display |
| CHAT-F-005 Create uniquely named rooms | Room module | `server/services/rooms.py`, `server/persistence/repository.py` | TC-ROOM-01 | `tests/test_rooms.py` | Implemented and behaviorally tested |
| CHAT-F-006 Join/leave rooms under permissions | Room module | `server/services/rooms.py`, `server/protocol/dispatcher.py` | TC-ROOM-02 | `tests/test_rooms.py`, `tests/test_admin.py` | Implemented and behaviorally tested |
| CHAT-F-007 Send direct or room messages | Message module | `server/services/router.py`, `server/protocol/dispatcher.py` | TC-MSG-01 | `tests/test_messaging.py`, `tests/test_rooms.py` | Implemented and behaviorally tested |
| CHAT-F-008 Deliver in sender order | Message router/connection queues | `server/services/router.py`, `server/transport/connection_manager.py` | TC-MSG-02 | `tests/test_messaging.py` | Implemented and behaviorally tested |
| CHAT-F-009 Reject oversized or invalid messages | Validation module | `server/protocol/framing.py`, `server/protocol/validator.py` | TC-MSG-03 | `tests/test_framing.py`, `tests/test_validator.py` | Implemented and behaviorally tested |
| CHAT-F-010 Report undelivered messages | Delivery module | `server/services/router.py`, `client/ui/app.py` | TC-MSG-04 | `tests/test_messaging.py`, `tests/test_history.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |
| CHAT-F-011 Persist messages | History/data module | `server/persistence/repository.py`, `server/persistence/schema.sql` | TC-HIST-01 | `tests/test_history.py` | Implemented and behaviorally tested |
| CHAT-F-012 Retrieve only permitted history | History/access-control modules | `server/services/router.py`, `server/persistence/repository.py` | TC-HIST-02 | `tests/test_history.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |
| CHAT-F-013 Notify room members of joins/leaves | Notification/room modules | `server/services/rooms.py`, `server/services/presence.py` | TC-NOTIF-01 | `tests/test_rooms.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |
| CHAT-F-014 Recover from unexpected disconnects | Connection manager | `server/transport/connection_manager.py`, `server/protocol/dispatcher.py` | TC-DISC-01 | `tests/test_connection.py` | Implemented and behaviorally tested |
| CHAT-F-015 Administer user accounts | Admin module | `server/services/admin.py`, `server/manage.py` | TC-ADMIN-01 | `tests/test_admin.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |
| CHAT-F-016 Administer rooms | Admin/room modules | `server/services/admin.py`, `server/services/rooms.py` | TC-ADMIN-02 | `tests/test_admin.py` | Implemented and behaviorally tested |
| CHAT-F-017 Log security/admin events without passwords | Logging module | `server/audit/audit_logger.py`, `server/main.py`, `server/persistence/repository.py` | TC-LOG-01 | `tests/test_admin.py`, `tests/test_auth.py` | Implemented and behaviorally tested |
| CHAT-F-018 Clean logout | Session module | `server/protocol/dispatcher.py`, `server/services/sessions.py` | TC-LOGOUT-01 | `tests/test_auth.py`, `tests/test_client_ui.py` | Implemented and behaviorally tested |

## Non-functional requirements

| SRS requirement | SAD design area | Implementation | STP case | Automated evidence | Coverage |
|---|---|---|---|---|---|
| CHAT-NF-001 90% of valid messages within 1 second under normal load | Performance | `server/services/router.py`, `server/transport/connection_manager.py` | TC-PERF-01 | `tests/test_messaging.py::test_50_authenticated_clients_concurrent_delivery_latency` | Pass in the recorded local sample: 50/50 messages delivered; P90 0.0971 s. This is a sample, not a general production guarantee. |
| CHAT-NF-002 At least 50 simultaneous authenticated clients | Scalability | `server/transport/connection_manager.py`, `server/services/presence.py` | TC-LOAD-01 | `tests/test_messaging.py::test_50_authenticated_clients_concurrent_delivery_latency` | Implemented and tested with 50 clients |
| CHAT-NF-003 Isolate individual client disconnects | Reliability | `server/transport/connection_manager.py` | TC-REL-01 | `tests/test_connection.py`, `tests/test_messaging.py` | Implemented and behaviorally tested |
| CHAT-NF-004 Clear, usable desktop status and error UI | Client UI | `client/ui/app.py` | TC-UX-01 | `tests/test_client_ui.py` | Implemented; UI tests were skipped locally because no graphical display was available |
| CHAT-NF-005 Encrypted traffic and no plaintext sensitive account data | Security/privacy | `client/net/connection.py`, `server/transport/connection_manager.py`, `server/services/auth.py` | TC-SEC-01 | `tests/test_auth.py`; TLS exercised by integration tests | TLS and credential-handling paths are implemented. The security case itself is not a comprehensive production TLS assessment; no certificate-rejection/downgrade suite is present. |
| CHAT-NF-006 Maintain persistent data integrity | Data integrity | `server/persistence/schema.sql`, `server/persistence/repository.py` | TC-DATA-01 | `tests/test_history.py`, `tests/test_admin.py` | Implemented and behaviorally tested for constraints, references, and append-only audit rows |
| CHAT-NF-007 Modular maintainable components | Maintainability | `client/`, `server/` package layers | TC-MAINT-01 | `tests/test_config.py`; architecture review | Implemented by structure; no dedicated automated maintainability test |

## Security requirements

| SRS requirement | SAD design area | Implementation | STP case | Automated evidence | Coverage |
|---|---|---|---|---|---|
| CHAT-SR-001 TLS for client/server traffic | Security/TLS | `client/net/connection.py`, `server/transport/connection_manager.py` | TC-SEC-02 | TLS-backed integration tests in `tests/test_connection.py`, `tests/test_auth.py` | TLS 1.2 minimum and certificate verification are implemented. Tests use a valid temporary self-signed certificate; certificate rejection and downgrade behavior are not independently tested. |
| CHAT-SR-002 Salted one-way password hashes; no plaintext password storage/logging | Authentication/logging | `server/services/auth.py`, `server/audit/audit_logger.py` | TC-SEC-03 | `tests/test_auth.py`, `tests/test_admin.py` | Implemented and behaviorally tested |
| CHAT-SR-003 Role-based authorization | Authorization | `server/services/admin.py`, `server/services/rooms.py`, `server/services/router.py` | TC-SEC-04 | `tests/test_admin.py`, `tests/test_rooms.py`, `tests/test_history.py` | Implemented and behaviorally tested |
| CHAT-SR-004 Validate message types, lengths, and fields | Input validation | `server/protocol/validator.py`, `server/protocol/framing.py` | TC-SEC-05 | `tests/test_validator.py`, `tests/test_framing.py` | Implemented and behaviorally tested |
| CHAT-SR-005 Protect logs and record security events | Audit/logging | `server/audit/audit_logger.py`, `server/persistence/schema.sql`, `server/main.py` | TC-SEC-06 | `tests/test_admin.py`, `tests/test_auth.py` | Redaction and SQLite append-only triggers are behaviorally tested. The database/host administrator remains able to modify files offline. |
| CHAT-SR-006 Expire inactive sessions by policy | Session module | `server/services/sessions.py`, `server/persistence/repository.py`, `server/app.py` | TC-SEC-07 | `tests/test_connection.py` verifies activity refresh; no expiry-focused test is present | Expiry enforcement and background cleanup are implemented; expiration behavior still needs dedicated automated verification. |

## Test-plan interpretation and latest evidence

The STP test IDs above are the submitted test-plan identifiers. The code suite also includes tests
whose Python names are shown above; tests may validate several requirements at once. In particular,
`tests/test_security.py` checks that security test-case IDs/objectives are documented; those
documentation checks do not themselves exercise each security objective. Behavioral evidence is
identified separately in the matrix.

Latest local verification (12 November 2026, Python 3.12.3, pytest 9.2.0):

- Full suite: **183 passed, 1 skipped**, in 58.32 seconds. The Tkinter UI test module was skipped
  because this environment has no display.
- 50-client test: **50 clients authenticated, 50 messages delivered**, average measured latency
  0.0579 seconds, P90 0.0971 seconds. The test passed the 1-second P90 threshold.
- See [issue-15-qa-validation.md](issue-15-qa-validation.md) for the run details and
  [issue-12-qa-test-plan.md](issue-12-qa-test-plan.md) for performance/recovery results.

## Open verification and operational limitations

- Run the Tkinter UI tests on a machine with a graphical display.
- Add a test that deliberately ages a session and verifies expiry, connection closure, and rejection
  of the expired token.
- Extend TLS tests to cover invalid certificates and protocol-version rejection. The local test
  certificate is not a production certificate or a full security audit.
- The client currently uses the fixed `certs/server.crt` trust-file path; certificate rotation and
  production provisioning need operational procedures.
- The application has one server and no clustering. Message history is SQLite data without
  application-level encryption at rest. Message writes are asynchronous, so a failed database
  write can occur after a message was delivered.
