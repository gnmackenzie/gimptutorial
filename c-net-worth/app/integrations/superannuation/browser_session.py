"""Playwright helpers for encrypted provider browser sessions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, async_playwright

from app.core.encrypted_session_store import EncryptedSessionStore


class ProviderBrowserSession:
    """Open browser contexts backed by encrypted Playwright storage state."""

    def __init__(
        self,
        provider_id: str,
        store: EncryptedSessionStore,
        headless: bool = True,
    ) -> None:
        """Configure a provider browser session.

        Args:
            provider_id: Stable provider identifier.
            store: Encrypted session-state store.
            headless: Whether Chromium runs without a visible window.
        """
        self._provider_id = provider_id
        self._store = store
        self._headless = headless

    @asynccontextmanager
    async def context(self) -> AsyncIterator[BrowserContext]:
        """Yield a browser context populated from encrypted state.

        Yields:
            Ready Playwright browser context.
        """
        async with async_playwright() as playwright:
            browser: Browser = await playwright.chromium.launch(
                headless=self._headless
            )
            state: dict[str, Any] | None = self._store.load(self._provider_id)
            context = await browser.new_context(storage_state=state)
            try:
                yield context
            finally:
                await context.close()
                await browser.close()

    async def save(self, context: BrowserContext) -> None:
        """Encrypt the current context storage state.

        Args:
            context: Authenticated Playwright browser context.
        """
        state = await context.storage_state(indexed_db=True)
        self._store.save(self._provider_id, state)

    def clear(self) -> None:
        """Delete stale or logged-out provider state."""
        self._store.delete(self._provider_id)
