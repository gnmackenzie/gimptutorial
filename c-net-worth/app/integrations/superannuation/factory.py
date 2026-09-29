"""Construct encrypted provider-browser dependencies."""

from pathlib import Path

from app.core.config import get_settings
from app.core.encrypted_session_store import EncryptedSessionStore
from app.integrations.superannuation.browser_session import ProviderBrowserSession


def provider_browser_session(provider_id: str) -> ProviderBrowserSession:
    """Build an encrypted browser session for one provider.

    Args:
        provider_id: Stable provider identifier.

    Returns:
        Provider browser-session helper.
    """
    settings = get_settings()
    store = EncryptedSessionStore.from_key_file(
        Path("/app/data/provider-state"),
        settings.session_encryption_keys_file,
    )
    return ProviderBrowserSession(provider_id, store)
