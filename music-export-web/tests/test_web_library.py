"""Tests for web-library discovery."""

from pathlib import Path

from music_to_mp3.web.library import scan_library


def test_scan_library_returns_supported_tracks(tmp_path: Path) -> None:
    """Count MP3 and FLAC files beneath artist and album paths."""

    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "one.flac").write_bytes(b"data")
    (album / "two.mp3").write_bytes(b"data")
    (album / "notes.txt").write_text("ignore", encoding="utf-8")
    summaries = scan_library(tmp_path)
    assert len(summaries) == 1
    assert summaries[0].tracks == 2
