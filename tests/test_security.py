"""Security test cases for Issue #14."""

import pytest


SECURITY_TEST_CASES = [
    {
        "id": "TC-SEC-01",
        "objective": "Verify overall security and privacy.",
    },
    {
        "id": "TC-SEC-02",
        "objective": "Verify encrypted client-server transport.",
    },
    {
        "id": "TC-SEC-03",
        "objective": "Verify passwords are stored as secure hashes.",
    },
    {
        "id": "TC-SEC-04",
        "objective": "Verify role-based authorization.",
    },
    {
        "id": "TC-SEC-05",
        "objective": "Verify malformed and oversized inputs are rejected.",
    },
    {
        "id": "TC-SEC-06",
        "objective": "Verify logs do not expose sensitive information.",
    },
    {
        "id": "TC-SEC-07",
        "objective": "Verify expired sessions are rejected.",
    },
]


@pytest.mark.parametrize(
    "test_case",
    SECURITY_TEST_CASES,
    ids=[case["id"] for case in SECURITY_TEST_CASES],
)
def test_security_case_is_documented(test_case):
    """Ensure each planned security case has an ID and objective."""
    assert test_case["id"].startswith("TC-SEC-")
    assert test_case["objective"]
