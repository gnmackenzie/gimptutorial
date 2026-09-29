"""Application configuration loaded from environment and secret files."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Define validated runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./networth.db"
    database_password_file: Path | None = None
    secret_key_file: Path = Path("/run/secrets/app_secret_key")
    session_encryption_keys_file: Path = Path(
        "/run/secrets/session_encryption_keys"
    )
    log_directory: Path = Path("logs")
    log_retention_days: int = Field(default=30, ge=1, le=365)
    session_cookie_secure: bool = False
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = Field(default=8883, ge=1, le=65535)
    mqtt_topic: str = "home/portfolio/total"
    mqtt_tls_enabled: bool = True
    mqtt_username_file: Path | None = None
    mqtt_password_file: Path | None = None
    fund_one_username_file: Path | None = None
    fund_one_password_file: Path | None = None
    fund_two_username_file: Path | None = None
    fund_two_password_file: Path | None = None

    @field_validator("mqtt_topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        """Reject wildcard subscriptions for the valuation consumer."""
        if "+" in value or "#" in value or not value.strip():
            raise ValueError("MQTT_TOPIC must be one concrete topic")
        return value

    def read_secret(self, path: Path | None) -> SecretStr | None:
        """Read a secret from a mounted file.

        Args:
            path: Path to a Docker secret, or None.

        Returns:
            Secret text, or None when no path was configured.
        """
        if path is None:
            return None
        return SecretStr(path.read_text(encoding="utf-8").strip())

    @property
    def secret_key(self) -> str:
        """Return the application session signing key."""
        return self.secret_key_file.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
