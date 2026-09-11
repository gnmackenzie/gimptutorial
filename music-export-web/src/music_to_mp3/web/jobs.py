"""Create, execute, cancel, and package long-running export jobs."""

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import shutil
from threading import Lock
from typing import Final
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from music_to_mp3.discovery import discover_jobs
from music_to_mp3.ffmpeg import validate_ffmpeg
from music_to_mp3.models import JobResult, Outcome
from music_to_mp3.processing import process_job
from music_to_mp3.selection import read_selection_file
from music_to_mp3.web.database import (
    add_event,
    create_job,
    get_job,
    increment_job,
    update_job,
    utc_now,
)
from music_to_mp3.web.settings import Destination, get_settings

_TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "failed", "cancelled", "ready"}
)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="export-job")
_active_lock = Lock()
_active_jobs: set[str] = set()


def submit_job(
    selection_text: str,
    destination_key: str,
    quality: int,
    overwrite: bool,
) -> str:
    """Persist and submit an export job.

    Args:
        selection_text: Validated selection-file content.
        destination_key: Configured destination identifier.
        quality: LAME VBR quality from zero through nine.
        overwrite: Whether existing output files may be replaced.

    Returns:
        Newly allocated job identifier.

    Raises:
        ValueError: If the destination or quality is invalid.
    """

    settings = get_settings()
    settings.destination(destination_key)
    if quality not in range(10):
        raise ValueError("Quality must be between 0 and 9")
    with _active_lock:
        if len(_active_jobs) >= settings.max_active_jobs:
            raise ValueError("The maximum number of active jobs has been reached")
        job_id = uuid4().hex
        _active_jobs.add(job_id)
    now = utc_now()
    create_job(
        {
            "id": job_id,
            "created_at": now,
            "updated_at": now,
            "status": "queued",
            "destination_key": destination_key,
            "selection_text": selection_text,
            "quality": quality,
            "overwrite": int(overwrite),
        }
    )
    _executor.submit(run_job, job_id)
    return job_id


def validate_destination(destination: Destination) -> None:
    """Ensure a destination is safe and available.

    Args:
        destination: Configured destination to validate.

    Raises:
        ValueError: If the destination cannot safely accept output.
    """

    destination.path.mkdir(parents=True, exist_ok=True)
    if destination.marker and not (destination.path / destination.marker).is_file():
        raise ValueError(
            f"USB marker {destination.marker!r} is missing from {destination.path}"
        )
    probe = destination.path / f".write-probe-{uuid4().hex}"
    try:
        probe.write_text("probe", encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Destination is not writable: {error}") from error
    finally:
        probe.unlink(missing_ok=True)


def selection_path(job_id: str, selection_text: str) -> Path:
    """Write job selection text to persistent temporary storage.

    Args:
        job_id: Job identifier.
        selection_text: Selection-file content.

    Returns:
        Path to the written selection file.
    """

    job_root = get_settings().data_root / "jobs" / job_id
    job_root.mkdir(parents=True, exist_ok=True)
    path = job_root / "selection.txt"
    path.write_text(selection_text, encoding="utf-8")
    return path


def run_job(job_id: str) -> None:
    """Run one persisted export job.

    Args:
        job_id: Existing job identifier.
    """

    try:
        job = get_job(job_id)
        if job is None:
            return
        settings = get_settings()
        destination = settings.destination(str(job["destination_key"]))
        validate_destination(destination)
        update_job(job_id, status="scanning")
        source_root = settings.source_root.resolve()
        output_root = (
            destination.path / job_id
            if destination.kind == "download"
            else destination.path
        )
        selection = read_selection_file(
            selection_path(job_id, str(job["selection_text"]))
        )
        audio_jobs, invalid_count = discover_jobs(source_root, output_root, selection)
        update_job(job_id, status="running", total_files=len(audio_jobs))
        if invalid_count:
            add_event(job_id, "warning", f"Ignored {invalid_count} file(s) with an invalid layout")
        if not audio_jobs:
            raise ValueError("The selection matched no MP3 or FLAC files")
        ffmpeg = validate_ffmpeg("ffmpeg")
        futures: dict[Future[JobResult], str] = {}
        with ThreadPoolExecutor(
            max_workers=settings.conversion_workers,
            thread_name_prefix=f"job-{job_id[:8]}",
        ) as worker:
            for audio_job in audio_jobs:
                futures[
                    worker.submit(
                        process_job,
                        audio_job,
                        ffmpeg=ffmpeg,
                        quality=int(job["quality"]),
                        overwrite=bool(job["overwrite"]),
                    )
                ] = os.fspath(audio_job.source)
            for future in as_completed(futures):
                current = get_job(job_id)
                if current and current["cancel_requested"]:
                    for pending in futures:
                        pending.cancel()
                    update_job(job_id, status="cancelled")
                    add_event(job_id, "warning", "Cancellation requested")
                    return
                result = future.result()
                counter = {
                    Outcome.COPIED: "copied_files",
                    Outcome.CONVERTED: "converted_files",
                    Outcome.SKIPPED: "skipped_files",
                    Outcome.FAILED: "failed_files",
                }[result.outcome]
                increment_job(job_id, processed_files=1, **{counter: 1})
                update_job(job_id, current_file=os.fspath(result.job.source))
                if result.outcome is Outcome.FAILED:
                    add_event(job_id, "error", f"{result.job.source}: {result.message}")

        final = get_job(job_id)
        if final is None:
            return
        if destination.kind == "download":
            update_job(job_id, status="packaging", current_file="Creating ZIP archive")
            archive_name = f"music-export-{job_id[:8]}.zip"
            archive_path = settings.download_root / archive_name
            create_archive(output_root, archive_path)
            shutil.rmtree(output_root, ignore_errors=True)
            update_job(job_id, status="ready", download_name=archive_name, current_file="")
        else:
            status = "completed" if not final["failed_files"] else "completed"
            update_job(job_id, status=status, current_file="")
    except Exception as error:
        update_job(job_id, status="failed", error=str(error), current_file="")
        add_event(job_id, "error", str(error))
    finally:
        with _active_lock:
            _active_jobs.discard(job_id)


def create_archive(source_root: Path, archive_path: Path) -> None:
    """Create a ZIP archive without retaining the staging root name.

    Args:
        source_root: Directory containing generated output.
        archive_path: ZIP file to create.
    """

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_suffix(".zip.part")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_root))
    os.replace(temporary, archive_path)


def request_cancellation(job_id: str) -> bool:
    """Request cancellation of a non-terminal job.

    Args:
        job_id: Job identifier.

    Returns:
        True if the request was recorded.
    """

    job = get_job(job_id)
    if job is None or job["status"] in _TERMINAL_STATUSES:
        return False
    update_job(job_id, cancel_requested=1)
    return True


def clean_expired_downloads() -> int:
    """Remove download archives older than the configured retention.

    Returns:
        Number of files removed.
    """

    settings = get_settings()
    threshold = datetime.now(UTC) - timedelta(hours=settings.download_retention_hours)
    removed = 0
    settings.download_root.mkdir(parents=True, exist_ok=True)
    for path in settings.download_root.glob("music-export-*.zip"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if modified < threshold:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
