"""Run the dedicated MQTT listener process."""

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.integrations.mqtt.client import build_client


def main() -> None:
    """Connect to the broker and process messages indefinitely."""
    settings = get_settings()
    configure_logging(settings.log_directory, settings.log_retention_days)
    client = build_client(settings)
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
