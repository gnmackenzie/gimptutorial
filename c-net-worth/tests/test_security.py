"""Tests for local account password security."""

from app.core.security import hash_password, verify_password


def test_password_round_trip() -> None:
    """Hash and verify a password without storing plaintext."""
    password_hash = hash_password("a-long-test-password")
    assert "a-long-test-password" not in password_hash
    assert verify_password(password_hash, "a-long-test-password")
    assert not verify_password(password_hash, "incorrect")
