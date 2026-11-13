# Issue #14 — Security Test Results

## Scope and evidence

The security-related automated evidence is distributed across the integration tests. The security
case list in `tests/test_security.py` only verifies that test-case IDs and objectives are
documented; it is not, by itself, a behavioral security test suite.

| Area | Automated evidence | Result / limitation |
|---|---|---|
| Password hashing and secret handling | `tests/test_auth.py`, `tests/test_admin.py` | Salted password hashes, no plaintext password/token persistence, password log redaction, and audit redaction are tested. |
| TLS transport | TLS-backed integration tests, including `tests/test_connection.py` and `tests/test_auth.py` | Valid TLS connections are exercised. Tests use an ephemeral self-signed certificate; certificate rejection, protocol downgrade, and production TLS configuration are not comprehensively tested. |
| Role-based authorization | `tests/test_admin.py`, `tests/test_rooms.py`, `tests/test_history.py` | Non-admin restrictions and membership/history access controls have behavioral tests. |
| Input validation | `tests/test_validator.py`, `tests/test_framing.py` | Invalid fields, malformed JSON, and oversized frames are tested. |
| Audit protection | `tests/test_admin.py` | Audit records are tested for redaction and SQLite update/delete rejection. This does not prevent an operating-system/database administrator from changing database files offline. |
| Session lifetime | `tests/test_connection.py` | Authenticated activity refresh is tested; expiry after an idle timeout has no dedicated behavioral test yet. |

## Latest regression run

On 12 November 2026, the full suite was run on Windows with Python 3.12.3 and pytest 9.2.0:

- **183 passed, 1 skipped**, in 58.32 seconds; no failures or errors.
- The Tkinter UI test module was skipped because the environment had no graphical display.
- The separate 50-client messaging test delivered 50/50 messages with a measured P90 latency of
  0.0971 seconds. This is a local sample, not a production guarantee.

See [requirements-traceability.md](../documents/requirements-traceability.md) for the full
SRS/SAD/STP matrix and [issue-15-qa-validation.md](../documents/issue-15-qa-validation.md) for
environment and run details.
