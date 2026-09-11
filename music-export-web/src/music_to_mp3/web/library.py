"""Scan the directory-based music library for the web interface."""

from dataclasses import dataclass
from pathlib import Path

from music_to_mp3.constants import SUPPORTED_SOURCE_SUFFIXES


@dataclass(frozen=True, slots=True)
class AlbumSummary:
    """Summarise one album directory.

    Attributes:
        artist: Artist directory name.
        album: Album directory name.
        tracks: Number of supported audio files found recursively.
    """

    artist: str
    album: str
    tracks: int


def scan_library(source_root: Path, query: str = "") -> list[AlbumSummary]:
    """Return albums found directly beneath artist directories.

    Args:
        source_root: Root containing artist and album directories.
        query: Optional case-insensitive substring filter.

    Returns:
        Sorted album summaries.
    """

    query_key = query.strip().casefold()
    summaries: list[AlbumSummary] = []
    if not source_root.is_dir():
        return summaries
    for artist_path in sorted(source_root.iterdir(), key=lambda p: p.name.casefold()):
        if not artist_path.is_dir():
            continue
        for album_path in sorted(artist_path.iterdir(), key=lambda p: p.name.casefold()):
            if not album_path.is_dir():
                continue
            searchable = f"{artist_path.name} {album_path.name}".casefold()
            if query_key and query_key not in searchable:
                continue
            tracks = sum(
                path.is_file()
                and path.suffix.casefold() in SUPPORTED_SOURCE_SUFFIXES
                for path in album_path.rglob("*")
            )
            if tracks:
                summaries.append(
                    AlbumSummary(artist_path.name, album_path.name, tracks)
                )
    return summaries
