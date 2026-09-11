"""Resolve FFmpeg and run FLAC-to-MP3 conversions."""

import os
from pathlib import Path
import shutil
import subprocess


def validate_ffmpeg(ffmpeg: str) -> str:
    """Resolve and test the FFmpeg executable.

    Args:
        ffmpeg: Command name or executable path supplied by the user.

    Returns:
        Resolved executable path.

    Raises:
        ValueError: If FFmpeg cannot be found or executed.
    """

    resolved = shutil.which(ffmpeg)
    if resolved is None:
        candidate = Path(ffmpeg).expanduser()
        if candidate.is_file():
            resolved = os.fspath(candidate.resolve())
        else:
            raise ValueError(
                f"FFmpeg executable not found: {ffmpeg!r}. Install FFmpeg "
                "or pass its path with --ffmpeg."
            )
    try:
        subprocess.run(
            [resolved, "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"Unable to run FFmpeg at {resolved!r}: {error}") from error
    return resolved


def encode_audio(
    ffmpeg: str,
    source: Path,
    temporary_output: Path,
    quality: int,
) -> None:
    """Convert one FLAC audio stream to MP3.

    Args:
        ffmpeg: Resolved FFmpeg executable.
        source: Source FLAC file.
        temporary_output: Temporary MP3 destination.
        quality: LAME VBR quality from zero through nine.

    Raises:
        RuntimeError: If FFmpeg returns a non-zero status.
    """

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        os.fspath(source),
        "-map",
        "0:a:0",
        "-map_metadata",
        "-1",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        str(quality),
        "-threads",
        "1",
        os.fspath(temporary_output),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "FFmpeg returned no error text")
