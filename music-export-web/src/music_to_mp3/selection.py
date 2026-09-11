"""Read and apply artist and album selections."""

from dataclasses import dataclass
from pathlib import Path
import re

from music_to_mp3.models import AlbumSelection


@dataclass(frozen=True, slots=True)
class Selection:
    """Contain artist and album criteria from a selection file.

    Attributes:
        artists: Artists for which all albums are selected.
        albums: Specific artist and album combinations.
    """

    artists: frozenset[str]
    albums: frozenset[AlbumSelection]

    def includes(self, artist: str, album: str) -> bool:
        """Determine whether an artist and album are selected.

        Args:
            artist: Artist directory name to test.
            album: Album directory name to test.

        Returns:
            True when an artist or album rule includes the combination.
        """

        artist_key = normalise_name(artist)
        album_key = normalise_name(album)
        return (
            artist_key in self.artists
            or AlbumSelection(artist_key, album_key) in self.albums
        )


def normalise_name(value: str) -> str:
    """Normalise a directory or selector name for exact matching.

    Args:
        value: Name to normalise.

    Returns:
        Case-folded name with surrounding whitespace removed.
    """

    return value.strip().casefold()


def parse_album_selector(value: str) -> AlbumSelection:
    r"""Parse an ``ARTIST/ALBUM`` or ``ARTIST\ALBUM`` selector.

    Args:
        value: Album selector from the selection file.

    Returns:
        Normalised artist and album selection.

    Raises:
        ValueError: If the selector is not composed of two non-empty parts.
    """

    parts = [part.strip() for part in re.split(r"[\/]", value, maxsplit=1)]
    if len(parts) != 2 or not all(parts):
        raise ValueError(
            f"Invalid album selector {value!r}; expected ARTIST/ALBUM"
        )
    return AlbumSelection(normalise_name(parts[0]), normalise_name(parts[1]))


def read_selection_file(selection_file: Path) -> Selection:
    """Read artist and album criteria from a UTF-8 text file.

    Args:
        selection_file: File containing one artist or artist/album per line.

    Returns:
        Immutable, normalised selection criteria.

    Raises:
        ValueError: If the file is unreadable, invalid, or empty.
    """

    try:
        lines = selection_file.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValueError(
            f"Unable to read selection file {selection_file}: {error}"
        ) from error

    artists: set[str] = set()
    albums: set[AlbumSelection] = set()
    for line_number, raw_line in enumerate(lines, start=1):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        if "/" in value or "\\" in value:
            try:
                albums.add(parse_album_selector(value))
            except ValueError as error:
                raise ValueError(
                    f"Selection file line {line_number}: {error}"
                ) from error
        else:
            artists.add(normalise_name(value))

    if not artists and not albums:
        raise ValueError(f"Selection file {selection_file} contains no selections")
    return Selection(frozenset(artists), frozenset(albums))
