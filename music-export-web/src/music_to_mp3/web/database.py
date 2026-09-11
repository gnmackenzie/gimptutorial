"""Provide the small SQLite persistence layer used by the web service."""

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from music_to_mp3.web.settings import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    destination_key TEXT NOT NULL,
    selection_text TEXT NOT NULL,
    quality INTEGER NOT NULL,
    overwrite INTEGER NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    processed_files INTEGER NOT NULL DEFAULT 0,
    copied_files INTEGER NOT NULL DEFAULT 0,
    converted_files INTEGER NOT NULL DEFAULT 0,
    skipped_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    current_file TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    download_name TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
"""


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 form.

    Returns:
        Timezone-aware timestamp string.
    """

    return datetime.now(UTC).isoformat()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Open a configured SQLite connection in a transaction.

    Yields:
        SQLite connection whose rows behave like mappings.
    """

    database_path = get_settings().database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(database_path, timeout=30)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA journal_mode = WAL")
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def initialise_database() -> None:
    """Create the database tables when they do not already exist."""

    with connection() as database:
        database.executescript(SCHEMA)


def create_job(record: dict[str, Any]) -> None:
    """Insert a new job.

    Args:
        record: Complete initial job values keyed by column name.
    """

    columns = ", ".join(record)
    placeholders = ", ".join("?" for _ in record)
    with connection() as database:
        database.execute(
            f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
            tuple(record.values()),
        )


def update_job(job_id: str, **changes: Any) -> None:
    """Update selected fields for a job.

    Args:
        job_id: Job identifier.
        **changes: Database columns and replacement values.
    """

    if not changes:
        return
    changes["updated_at"] = utc_now()
    assignments = ", ".join(f"{column} = ?" for column in changes)
    with connection() as database:
        database.execute(
            f"UPDATE jobs SET {assignments} WHERE id = ?",
            (*changes.values(), job_id),
        )


def increment_job(job_id: str, **increments: int) -> None:
    """Atomically increment job counters.

    Args:
        job_id: Job identifier.
        **increments: Counter columns and amounts to add.
    """

    if not increments:
        return
    assignments = ", ".join(
        f"{column} = {column} + ?" for column in increments
    )
    with connection() as database:
        database.execute(
            f"UPDATE jobs SET {assignments}, updated_at = ? WHERE id = ?",
            (*increments.values(), utc_now(), job_id),
        )


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return one job as a dictionary.

    Args:
        job_id: Job identifier.

    Returns:
        Job mapping, or None when it does not exist.
    """

    with connection() as database:
        row = database.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent jobs in descending creation order.

    Args:
        limit: Maximum number of jobs to return.

    Returns:
        Recent job mappings.
    """

    with connection() as database:
        rows = database.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def add_event(job_id: str, level: str, message: str) -> None:
    """Append a diagnostic event to a job.

    Args:
        job_id: Job identifier.
        level: Severity such as info, warning, or error.
        message: Human-readable event text.
    """

    with connection() as database:
        database.execute(
            "INSERT INTO job_events (job_id, created_at, level, message) "
            "VALUES (?, ?, ?, ?)",
            (job_id, utc_now(), level, message),
        )


def list_events(job_id: str) -> list[dict[str, Any]]:
    """Return events for one job.

    Args:
        job_id: Job identifier.

    Returns:
        Events in creation order.
    """

    with connection() as database:
        rows = database.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY id", (job_id,)
        ).fetchall()
    return [dict(row) for row in rows]
