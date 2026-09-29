"""Placeholder MQTT portfolio message schema."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PortfolioMessage(BaseModel):
    """Validate a total share-portfolio valuation message."""

    schema_version: int = Field(ge=1, le=1)
    portfolio_id: str = Field(min_length=1, max_length=160)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    market_value: Decimal = Field(ge=0)
    valuation_time: datetime
    message_id: UUID

    @field_validator("valuation_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require an unambiguous timestamp.

        Args:
            value: Parsed valuation timestamp.

        Returns:
            The timezone-aware timestamp.
        """
        if value.tzinfo is None:
            raise ValueError("valuation_time must include a timezone")
        return value
