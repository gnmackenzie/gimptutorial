"""Password hashing and session helpers."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: User-provided password.

    Returns:
        Encoded Argon2 password hash.
    """
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a password without exposing its value.

    Args:
        password_hash: Stored Argon2 hash.
        password: Candidate password.

    Returns:
        True when the password matches.
    """
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
