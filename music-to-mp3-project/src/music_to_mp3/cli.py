"""Command-line interface and concurrent job coordination."""

import os
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from music_to_mp3.constants import APP_NAME
from music_to_mp3.discovery import discover_jobs
from music_to_mp3.ffmpeg import validate_ffmpeg
from music_to_mp3.models import AudioJob, JobResult, Outcome
from music_to_mp3.processing import process_job
from music_to_mp3.selection import Selection, normalise_name, read_selection_file

app = typer.Typer(
    name=APP_NAME,
    add_completion=False,
    no_args_is_help=True,
    help="Copy MP3s and convert FLACs using an artist and album selection file.",
)
console = Console()


def report_missing_selections(
    source_root: Path,
    selection: Selection,
    jobs: list[AudioJob],
) -> None:
    """Warn about selectors that matched no supported audio files.

    Args:
        source_root: Source root displayed for context.
        selection: Requested artist and album criteria.
        jobs: Discovered jobs matching those criteria.
    """

    matched_artists = {normalise_name(job.artist) for job in jobs}
    matched_albums = {
        (normalise_name(job.artist), normalise_name(job.album)) for job in jobs
    }
    for artist in sorted(selection.artists - matched_artists):
        console.print(
            f"[yellow]Warning:[/yellow] artist {artist!r} matched no MP3 or "
            f"FLAC files beneath {source_root}."
        )
    for album in sorted(selection.albums, key=lambda item: (item.artist, item.album)):
        if (album.artist, album.album) not in matched_albums:
            console.print(
                "[yellow]Warning:[/yellow] album "
                f"{album.artist!r}/{album.album!r} matched no MP3 or FLAC files."
            )


@app.command()
def main(
    source_directory: Annotated[
        Path,
        typer.Argument(
            help="Root containing ARTIST/ALBUM directories.",
            exists=True,
            file_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    output_directory: Annotated[
        Path,
        typer.Argument(
            help="Root beneath which the selected MP3 tree is created.",
            file_okay=False,
            resolve_path=True,
        ),
    ],
    selection_file: Annotated[
        Path,
        typer.Argument(
            help="UTF-8 file containing one ARTIST or ARTIST/ALBUM per line.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    workers: Annotated[
        int,
        typer.Option("--workers", "-j", min=1, max=64),
    ] = min(4, os.cpu_count() or 1),
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", min=0, max=9),
    ] = 0,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite"),
    ] = False,
    ffmpeg: Annotated[str, typer.Option("--ffmpeg")] = "ffmpeg",
) -> None:
    """Copy MP3s and convert FLACs listed in a selection file.

    Args:
        source_directory: Root containing source artist directories.
        output_directory: Root for the mirrored output library.
        selection_file: UTF-8 file containing artist and album criteria.
        workers: Maximum concurrent worker threads.
        quality: LAME VBR quality used for FLAC conversion.
        overwrite: Whether existing destination files may be replaced.
        ffmpeg: FFmpeg command name or executable path.
    """

    try:
        selection = read_selection_file(selection_file)
        ffmpeg_executable = validate_ffmpeg(ffmpeg)
        jobs, invalid_layout_count = discover_jobs(
            source_directory,
            output_directory,
            selection,
        )
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=2) from error

    report_missing_selections(source_directory, selection, jobs)
    if invalid_layout_count:
        console.print(
            f"[yellow]Warning:[/yellow] ignored {invalid_layout_count:,} "
            "supported file(s) without artist and album directories."
        )
    if not jobs:
        console.print("No selected MP3 or FLAC files were found.")
        return

    copy_count = sum(job.action.value == "copy" for job in jobs)
    console.print(
        f"Selected {len(jobs):,} file(s): {copy_count:,} to copy and "
        f"{len(jobs) - copy_count:,} to convert. Using {workers} worker(s)."
    )
    counts = {outcome: 0 for outcome in Outcome}
    failures: list[JobResult] = []
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    with progress, ThreadPoolExecutor(max_workers=workers) as executor:
        task_id = progress.add_task("Processing", total=len(jobs))
        futures: dict[Future[JobResult], AudioJob] = {
            executor.submit(
                process_job,
                job,
                ffmpeg=ffmpeg_executable,
                quality=quality,
                overwrite=overwrite,
            ): job
            for job in jobs
        }
        try:
            for future in as_completed(futures):
                result = future.result()
                counts[result.outcome] += 1
                if result.outcome is Outcome.FAILED:
                    failures.append(result)
                progress.update(task_id, advance=1)
        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            raise typer.Exit(code=130) from None

    console.print(
        "Completed: "
        f"[green]{counts[Outcome.COPIED]:,} copied[/green], "
        f"[green]{counts[Outcome.CONVERTED]:,} converted[/green], "
        f"[yellow]{counts[Outcome.SKIPPED]:,} skipped[/yellow], "
        f"[red]{counts[Outcome.FAILED]:,} failed[/red]."
    )
    if failures:
        for result in failures:
            console.print(f"[red]{result.job.source}:[/red] {result.message}")
        raise typer.Exit(code=1)
