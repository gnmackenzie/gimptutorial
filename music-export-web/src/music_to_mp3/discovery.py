"""Discover selected audio files and map output paths."""

import os
from pathlib import Path

from music_to_mp3.constants import SUPPORTED_SOURCE_SUFFIXES
from music_to_mp3.models import AudioJob, JobAction
from music_to_mp3.selection import Selection


def path_artist_and_album(
    source_file: Path,
    source_root: Path,
) -> tuple[str, str] | None:
    """Read artist and album names from a relative directory path.

    Args:
        source_file: Audio file beneath the source root.
        source_root: Root of the source music library.

    Returns:
        Artist and album names, or None when either component is absent.
    """

    relative_path = source_file.relative_to(source_root)
    if len(relative_path.parts) < 3:
        return None
    return relative_path.parts[0], relative_path.parts[1]


def discover_jobs(
    source_root: Path,
    output_root: Path,
    selection: Selection,
) -> tuple[list[AudioJob], int]:
    """Find selected MP3 and FLAC files and build processing jobs.

    Args:
        source_root: Root directory containing artist directories.
        output_root: Root directory for the mirrored MP3 library.
        selection: Artist and album criteria.

    Returns:
        Jobs and the count of supported files with an invalid layout.

    Raises:
        ValueError: If source and output are the same directory or if two
            source files map to the same output path.
    """

    source_resolved = source_root.resolve()
    output_resolved = output_root.resolve()
    if source_resolved == output_resolved:
        raise ValueError("Source and output directories must be different")

    jobs_by_destination: dict[Path, AudioJob] = {}
    invalid_layout_count = 0
    source_files = sorted(
        source_resolved.rglob("*"),
        key=lambda path: os.fspath(path).casefold(),
    )
    for source_file in source_files:
        suffix = source_file.suffix.casefold()
        if not source_file.is_file() or suffix not in SUPPORTED_SOURCE_SUFFIXES:
            continue
        identity = path_artist_and_album(source_file, source_resolved)
        if identity is None:
            invalid_layout_count += 1
            continue
        artist, album = identity
        if not selection.includes(artist, album):
            continue

        relative_path = source_file.relative_to(source_resolved)
        destination = (output_resolved / relative_path).with_suffix(".mp3")
        action = JobAction.COPY if suffix == ".mp3" else JobAction.CONVERT
        job = AudioJob(source_file, destination, action, artist, album)
        existing = jobs_by_destination.get(destination)
        if existing is not None:
            if existing.action is JobAction.COPY:
                continue
            if job.action is JobAction.COPY:
                jobs_by_destination[destination] = job
                continue
            raise ValueError(
                f"Multiple source files map to output {destination}: "
                f"{existing.source} and {source_file}"
            )
        jobs_by_destination[destination] = job

    jobs = sorted(
        jobs_by_destination.values(),
        key=lambda job: os.fspath(job.source).casefold(),
    )
    return jobs, invalid_layout_count
