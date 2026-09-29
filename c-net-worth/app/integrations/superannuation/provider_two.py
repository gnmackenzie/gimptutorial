"""Safe placeholder adapter for superannuation provider two."""

from app.integrations.superannuation.base import (
    ProviderResult,
    ProviderStatus,
    SuperannuationProvider,
)


class ProviderTwo(SuperannuationProvider):
    """Represent provider two until its URL and selectors are configured."""

    async def retrieve_valuation(self) -> ProviderResult:
        """Stop at the explicit MFA integration boundary."""
        return ProviderResult(
            status=ProviderStatus.INTERACTION_REQUIRED,
            user_message=(
                "Provider two requires configured navigation and user-assisted MFA. "
                "No authentication bypass was attempted."
            ),
        )
