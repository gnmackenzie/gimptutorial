"""MQTT client and idempotent message processing."""

import hashlib
import logging
from datetime import datetime, UTC

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.database.session import SessionLocal
from app.models.entities import Account, Valuation, ValuationSource
from app.schemas.mqtt import PortfolioMessage

LOGGER = logging.getLogger(__name__)


def process_message(payload: bytes) -> None:
    """Validate and persist one placeholder-schema portfolio message.

    Args:
        payload: Raw MQTT payload bytes.
    """
    try:
        message = PortfolioMessage.model_validate_json(payload)
    except ValidationError:
        LOGGER.exception("Rejected invalid portfolio message")
        return
    with SessionLocal() as session:
        account = session.scalar(
            select(Account).where(Account.external_reference == message.portfolio_id)
        )
        if account is None or account.account_type != "SHARE_PORTFOLIO":
            LOGGER.error("No share account for portfolio_id=%s", message.portfolio_id)
            return
        session.add(
            Valuation(
                account_id=account.id,
                amount=message.market_value,
                currency=message.currency,
                valuation_time=message.valuation_time,
                received_time=datetime.now(UTC),
                source=ValuationSource.MQTT.value,
                source_reference=str(message.message_id),
                raw_payload_hash=hashlib.sha256(payload).hexdigest(),
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            LOGGER.info("Ignored duplicate MQTT message id=%s", message.message_id)
        else:
            LOGGER.info("Stored portfolio valuation id=%s", message.message_id)


def build_client(settings: Settings) -> mqtt.Client:
    """Build a configured MQTT 5 client.

    Args:
        settings: Validated application settings.

    Returns:
        Configured Paho client.
    """
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv5,
    )
    username = settings.read_secret(settings.mqtt_username_file)
    password = settings.read_secret(settings.mqtt_password_file)
    if username is not None:
        client.username_pw_set(
            username.get_secret_value(),
            password.get_secret_value() if password is not None else None,
        )
    if settings.mqtt_tls_enabled:
        client.tls_set()

    def on_connect(  # type: ignore[no-untyped-def]
        connected_client, _userdata, _flags, reason_code, _properties
    ) -> None:
        if reason_code != 0:
            LOGGER.error("MQTT connection failed reason=%s", reason_code)
            return
        connected_client.subscribe(settings.mqtt_topic, qos=1)
        LOGGER.info("Subscribed to MQTT valuation topic")

    def on_message(_client, _userdata, message) -> None:  # type: ignore[no-untyped-def]
        process_message(message.payload)

    client.on_connect = on_connect
    client.on_message = on_message
    return client
