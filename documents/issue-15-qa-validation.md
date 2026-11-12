# Issue #15 – QA Validation Results

## Test Execution

- Test framework: pytest
- Command: `py -3.12 -m pytest -v`
- Environment: Windows, Python 3.12.3, pytest 9.2.0
- Executed: 184 test outcomes
- Passed: 183
- Skipped: 1
- Failed: 0
- Errors: 0
- Execution time: 58.32 seconds

## Result

All tests that ran passed. The one skip is the Tkinter UI test module: this machine did not have a
graphical display available. The UI tests therefore still need to run in a desktop environment.

The separate 50-client performance/concurrency test passed:

- Authenticated clients: 50
- Messages delivered: 50 of 50
- Average observed latency: 0.0579 seconds
- P90 observed latency: 0.0971 seconds (acceptance threshold: at most 1 second)
- P50/P99: not reported by the test

The measured latency describes this one local test run only. It is not a production performance
guarantee.

## Test environment and certificate handling

The server requires a certificate/private-key pair. The repository does not include the private
key, so a temporary self-signed test pair was generated for this run, used by the network tests,
and removed afterward; the tracked `certs/server.crt` was restored. The CI workflow likewise
generates a test certificate and key before running the suite. Never commit a private key.

## Known gaps and limitations

- UI tests were not exercised in this headless run.
- Session idle expiry is implemented, but no dedicated test forces a session past its timeout and
  checks expiry/connection cleanup.
- The STP security IDs are listed in `tests/test_security.py`; that file verifies the IDs and
  objectives are documented, not that every security objective was behaviorally tested. The
  behavioral evidence available in other test modules is mapped in
  [requirements-traceability.md](requirements-traceability.md).
- TLS-backed tests use a valid temporary certificate. They do not constitute a production TLS
  assessment and do not test certificate rejection or protocol downgrade.
- Message history is stored in SQLite without application-level encryption at rest. The server is
  single-instance; clustering and high availability are not implemented.

See [issue-12-qa-test-plan.md](issue-12-qa-test-plan.md) for the recorded concurrency/recovery
measurements and [requirements-traceability.md](requirements-traceability.md) for SRS/SAD/STP
coverage.