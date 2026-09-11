"""Application constants."""

from typing import Final

APP_NAME: Final[str] = "music-to-mp3"
SUPPORTED_SOURCE_SUFFIXES: Final[frozenset[str]] = frozenset({".flac", ".mp3"})
COVER_STEMS: Final[tuple[str, ...]] = (
    "cover",
    "folder",
    "front",
    "album",
    "albumart",
)
IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)
