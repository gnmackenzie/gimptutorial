"""Copy MP3 files and coordinate FLAC conversions."""

import os
from pathlib import Path
import shutil
import tempfile

from music_to_mp3.artwork import find_cover_art
from music_to_mp3.ffmpeg import encode_audio
from music_to_mp3.metadata import copy_flac_metadata
from music_to_mp3.models import AudioJob, JobAction, JobResult, Outcome


def create_temporary_mp3(destination: Path) -> Path:
    """Create an empty temporary MP3 beside its final destination.

    Args:
        destination: Final MP3 output path.

    Returns:
        Path to an empty temporary MP3 file.
    """

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.",
        suffix=".mp3",
        dir=destination.parent,
    )
    os.close(descriptor)
    return Path(temporary_name)


def process_job(
    job: AudioJob,
    *,
    ffmpeg: str,
    quality: int,
    overwrite: bool,
) -> JobResult:
    """Copy or convert one audio file with atomic final replacement.

    Args:
        job: Copy or conversion operation to perform.
        ffmpeg: Resolved FFmpeg executable.
        quality: LAME VBR quality for FLAC conversion.
        overwrite: Whether an existing destination may be replaced.

    Returns:
        Result describing the operation's outcome.
    """

    if job.destination.exists() and not overwrite:
        return JobResult(job, Outcome.SKIPPED, "destination exists")

    job.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        temporary_path = create_temporary_mp3(job.destination)
        if job.action is JobAction.COPY:
            shutil.copy2(job.source, temporary_path)
            outcome = Outcome.COPIED
        else:
            encode_audio(ffmpeg, job.source, temporary_path, quality)
            copy_flac_metadata(
                job.source,
                temporary_path,
                find_cover_art(job.source.parent),
            )
            outcome = Outcome.CONVERTED
        os.replace(temporary_path, job.destination)
        temporary_path = None
        return JobResult(job, outcome)
    except Exception as error:
        return JobResult(job, Outcome.FAILED, str(error))
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
