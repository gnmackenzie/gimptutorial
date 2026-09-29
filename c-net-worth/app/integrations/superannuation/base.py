"""Common contract for MFA-protected provider adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ProviderStatus(StrEnum):
    """Result states for a provider refresh."""

    SUCCESS = "SUCCESS"
    INTERACTION_REQUIRED = "INTERACTION_REQUIRED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class FundValuation:
    """Validated fund balance returned by a provider."""

    balance: Decimal
    currency: str
    valuation_time: datetime
    account_reference: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Outcome of a provider refresh attempt."""

    status: ProviderStatus
    valuation: FundValuation | None = None
    user_message: str | None = None


class SuperannuationProvider(ABC):
    """Define the boundary implemented by each provider."""

    @abstractmethod
    async def retrieve_valuation(self) -> ProviderResult:
        """Log in, respect MFA, and retrieve a validated valuation."""
