"""Tests for encrypted MFA browser-state persistence."""

from pathlib import Path

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.encrypted_session_store import EncryptedSessionStore


def test_state_is_encrypted_and_round_trips(tmp_path: Path) -> None:
    """Persist state without leaving cookie values in plaintext."""
    store = EncryptedSessionStore(tmp_path, [Fernet.generate_key()])
    state = {"cookies": [{"name": "session", "value": "sensitive-token"}]}
    store.save("provider-one", state)
    ciphertext = (tmp_path / "provider-one.state.enc").read_bytes()
    assert b"sensitive-token" not in ciphertext
    assert store.load("provider-one") == state


def test_wrong_key_cannot_decrypt(tmp_path: Path) -> None:
    """Reject state that cannot be authenticated by the configured key."""
    first = EncryptedSessionStore(tmp_path, [Fernet.generate_key()])
    first.save("provider-one", {"cookies": []})
    second = EncryptedSessionStore(tmp_path, [Fernet.generate_key()])
    with pytest.raises(InvalidToken):
        second.load("provider-one")


def test_rotation_uses_new_primary_key(tmp_path: Path) -> None:
    """Rotate existing ciphertext to the newest key."""
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    old_store = EncryptedSessionStore(tmp_path, [old_key])
    old_store.save("provider-one", {"cookies": []})
    rotating = EncryptedSessionStore(tmp_path, [new_key, old_key])
    rotating.rotate("provider-one")
    new_only = EncryptedSessionStore(tmp_path, [new_key])
    assert new_only.load("provider-one") == {"cookies": []}
