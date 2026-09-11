"""Load and validate application settings from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Destination(BaseModel):
    """Describe one server-side export destination.

    Attributes:
        key: Stable identifier submitted by web forms.
        label: Human-readable name shown in the interface.
        path: Container path used for output.
        kind: Either ``filesystem``, ``usb``, or ``download``.
        marker: Optional marker filename required at the destination root.
    """

    key: str
    label: str
    path: Path
    kind: str = "filesystem"
    marker: str | None = None


class Settings(BaseSettings):
    """Application settings read from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MUSIC_EXPORT_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Music Export"
    source_root: Path = Path("/music/source")
    data_root: Path = Path("/app/data")
    download_root: Path = Path("/app/downloads")
    nas_output: Path = Path("/destinations/nas")
    usb_output: Path = Path("/destinations/usb")
    usb_marker: str = ".music-export-usb"
    conversion_workers: int = Field(default=4, ge=1, le=64)
    max_active_jobs: int = Field(default=1, ge=1, le=4)
    download_retention_hours: int = Field(default=24, ge=1, le=720)
    max_selection_upload_bytes: int = Field(default=1_048_576, ge=1024)

    @property
    def database_path(self) -> Path:
        """Return the SQLite database path.

        Returns:
            Path beneath the persistent application data directory.
        """

        return self.data_root / "music-export.sqlite3"

    def destinations(self) -> tuple[Destination, ...]:
        """Return destinations permitted by the deployment configuration.

        Returns:
            Immutable sequence of server-side and browser destinations.
        """

        return (
            Destination("nas", "NAS output directory", self.nas_output),
            Destination(
                "usb",
                "USB device mounted on NAS",
                self.usb_output,
                kind="usb",
                marker=self.usb_marker,
            ),
            Destination(
                "download",
                "Download ZIP to this computer",
                self.download_root,
                kind="download",
            ),
        )

    def destination(self, key: str) -> Destination:
        """Find an allowed destination by key.

        Args:
            key: Destination identifier from a submitted form.

        Returns:
            Matching configured destination.

        Raises:
            ValueError: If the key is not configured.
        """

        for destination in self.destinations():
            if destination.key == key:
                return destination
        raise ValueError(f"Unknown destination: {key}")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached settings object.

    Returns:
        Validated settings.
    """

    return Settings()
