"""Encrypted persistence for sensitive Playwright authentication state."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class EncryptedSessionStore:
    """Encrypt browser storage state with authenticated symmetric encryption.

    The first key encrypts new state. Remaining keys permit decryption of older
    state and support controlled key rotation.
    """

    def __init__(self, root: Path, keys: list[bytes]) -> None:
        """Create an encrypted session store.

        Args:
            root: Private directory containing encrypted provider state.
            keys: Fernet keys ordered newest first.

        Raises:
            ValueError: If no encryption keys are provided.
        """
        if not keys:
            raise ValueError("At least one session encryption key is required")
        self._root = root
        self._cipher = MultiFernet([Fernet(key) for key in keys])
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._root, 0o700)

    @classmethod
    def from_key_file(cls, root: Path, key_file: Path) -> "EncryptedSessionStore":
        """Load one or more newline-separated keys from a Docker secret.

        Args:
            root: Private state directory.
            key_file: Read-only secret file with newest key first.

        Returns:
            Configured encrypted store.
        """
        keys = [
            line.strip().encode("ascii")
            for line in key_file.read_text(encoding="ascii").splitlines()
            if line.strip()
        ]
        return cls(root, keys)

    def exists(self, provider_id: str) -> bool:
        """Return whether encrypted state exists for a provider.

        Args:
            provider_id: Stable provider identifier.

        Returns:
            True when encrypted state exists.
        """
        return self._path(provider_id).is_file()

    def save(self, provider_id: str, state: dict[str, Any]) -> None:
        """Encrypt and atomically persist Playwright storage state.

        Args:
            provider_id: Stable provider identifier.
            state: Storage state returned by Playwright.
        """
        plaintext = json.dumps(
            state, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        token = self._cipher.encrypt(plaintext)
        destination = self._path(provider_id)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self._root, prefix=f".{provider_id}-", suffix=".tmp"
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(token)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, destination)
            os.chmod(destination, 0o600)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def load(self, provider_id: str) -> dict[str, Any] | None:
        """Decrypt stored Playwright state.

        Args:
            provider_id: Stable provider identifier.

        Returns:
            Decrypted state, or None when no state exists.

        Raises:
            InvalidToken: If the state cannot be authenticated or decrypted.
        """
        path = self._path(provider_id)
        if not path.exists():
            return None
        plaintext = self._cipher.decrypt(path.read_bytes())
        value = json.loads(plaintext)
        if not isinstance(value, dict):
            raise InvalidToken
        return value

    def delete(self, provider_id: str) -> None:
        """Delete encrypted state for a provider.

        Args:
            provider_id: Stable provider identifier.
        """
        self._path(provider_id).unlink(missing_ok=True)

    def rotate(self, provider_id: str) -> None:
        """Re-encrypt existing state with the newest configured key.

        Args:
            provider_id: Stable provider identifier.
        """
        path = self._path(provider_id)
        if not path.exists():
            return
        rotated = self._cipher.rotate(path.read_bytes())
        path.write_bytes(rotated)
        os.chmod(path, 0o600)

    def _path(self, provider_id: str) -> Path:
        """Return a safe state path for a provider identifier."""
        if not provider_id or not provider_id.replace("-", "").isalnum():
            raise ValueError("Invalid provider identifier")
        return self._root / f"{provider_id}.state.enc"
