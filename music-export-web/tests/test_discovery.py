"""Tests for directory-based job discovery."""

from pathlib import Path

from music_to_mp3.discovery import discover_jobs
from music_to_mp3.models import JobAction
from music_to_mp3.selection import Selection


def test_existing_mp3_wins_over_matching_flac(tmp_path: Path) -> None:
    """Prefer a source MP3 when FLAC and MP3 map to the same output."""

    source = tmp_path / "source"
    output = tmp_path / "output"
    album = source / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "Track.flac").write_bytes(b"flac")
    (album / "Track.mp3").write_bytes(b"mp3")
    selection = Selection(frozenset({"artist"}), frozenset())

    jobs, invalid_count = discover_jobs(source, output, selection)

    assert invalid_count == 0
    assert len(jobs) == 1
    assert jobs[0].action is JobAction.COPY
    assert jobs[0].source.name == "Track.mp3"
