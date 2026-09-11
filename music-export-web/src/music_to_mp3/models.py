"""Typed models used across the application."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class JobAction(str, Enum):
    """Describe the operation required for a source audio file."""

    COPY = "copy"
    CONVERT = "convert"


class Outcome(str, Enum):
    """Describe the result of processing one audio file."""

    COPIED = "copied"
    CONVERTED = "converted"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AlbumSelection:
    """Identify one album belonging to one artist.

    Attributes:
        artist: Normalised artist directory name.
        album: Normalised album directory name.
    """

    artist: str
    album: str


@dataclass(frozen=True, slots=True)
class AudioJob:
    """Describe one immutable copy or conversion operation.

    Attributes:
        source: Existing source audio file.
        destination: Corresponding MP3 path beneath the output root.
        action: Whether the file is copied or converted.
        artist: Artist obtained from the relative source path.
        album: Album obtained from the relative source path.
    """

    source: Path
    destination: Path
    action: JobAction
    artist: str
    album: str


@dataclass(frozen=True, slots=True)
class JobResult:
    """Contain the result returned by a worker thread.

    Attributes:
        job: Job that was processed.
        outcome: Result category.
        message: Diagnostic information for skipped or failed jobs.
    """

    job: AudioJob
    outcome: Outcome
    message: str = ""
