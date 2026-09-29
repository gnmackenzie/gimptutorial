"""Safe placeholder adapter for superannuation provider one."""

from app.integrations.superannuation.base import (
    ProviderResult,
    ProviderStatus,
    SuperannuationProvider,
)


class ProviderOne(SuperannuationProvider):
    """Represent provider one until its URL and selectors are configured."""

    async def retrieve_valuation(self) -> ProviderResult:
        """Stop at the explicit MFA integration boundary."""
        return ProviderResult(
            status=ProviderStatus.INTERACTION_REQUIRED,
            user_message=(
                "Provider one requires configured navigation and user-assisted MFA. "
                "No authentication bypass was attempted."
            ),
        )
