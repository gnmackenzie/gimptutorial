"""Run periodic provider checks without bypassing MFA."""

import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.integrations.superannuation.provider_one import ProviderOne
from app.integrations.superannuation.provider_two import ProviderTwo

LOGGER = logging.getLogger(__name__)


async def run() -> None:
    """Check both provider adapters every six hours."""
    providers = (ProviderOne(), ProviderTwo())
    while True:
        for provider in providers:
            result = await provider.retrieve_valuation()
            LOGGER.info(
                "Provider refresh status=%s message=%s",
                result.status,
                result.user_message,
            )
        await asyncio.sleep(6 * 60 * 60)


def main() -> None:
    """Configure logging and start the provider worker."""
    settings = get_settings()
    configure_logging(settings.log_directory, settings.log_retention_days)
    asyncio.run(run())


if __name__ == "__main__":
    main()
