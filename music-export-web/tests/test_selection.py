"""Tests for selection-file parsing and matching."""

from pathlib import Path

import pytest

from music_to_mp3.models import AlbumSelection
from music_to_mp3.selection import read_selection_file


def test_selection_file_supports_artists_albums_and_comments(tmp_path: Path) -> None:
    """Parse artist and album entries while ignoring comments."""

    selection_file = tmp_path / "selection.txt"
    selection_file.write_text(
        "# comment\nPink Floyd\nDavid Bowie/Low\n\n",
        encoding="utf-8",
    )
    selection = read_selection_file(selection_file)
    assert selection.artists == frozenset({"pink floyd"})
    assert selection.albums == frozenset({AlbumSelection("david bowie", "low")})
    assert selection.includes("PINK FLOYD", "Meddle")
    assert selection.includes("David Bowie", "Low")
    assert not selection.includes("David Bowie", "Heroes")


def test_empty_selection_file_is_rejected(tmp_path: Path) -> None:
    """Reject a selection file containing no usable entries."""

    selection_file = tmp_path / "selection.txt"
    selection_file.write_text("# only a comment\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contains no selections"):
        read_selection_file(selection_file)
