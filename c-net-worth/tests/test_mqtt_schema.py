"""Tests for the placeholder MQTT contract."""

from app.schemas.mqtt import PortfolioMessage


def test_placeholder_message_is_valid() -> None:
    """Accept the documented portfolio total message."""
    message = PortfolioMessage.model_validate(
        {
            "schema_version": 1,
            "portfolio_id": "primary-share-portfolio",
            "currency": "AUD",
            "market_value": "487321.64",
            "valuation_time": "2026-09-28T06:00:00Z",
            "message_id": "1ea81937-63f7-46c6-b654-d51d35005c51",
        }
    )
    assert str(message.market_value) == "487321.64"
