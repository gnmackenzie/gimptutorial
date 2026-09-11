# Music Export

A FastAPI and HTMX service for selectively exporting a directory-based music
library. Existing MP3 files are copied unchanged. FLAC files are converted with
FFmpeg while metadata and cover art are retained.

## Features

- Browse and search artists and albums from the NAS music library.
- Upload a UTF-8 artist and album selection file.
- Export to a NAS directory.
- Export to a USB device mounted on the NAS.
- Stage output as a ZIP for download to the user's computer.
- Run conversions in multiple worker threads.
- Record jobs, counters, errors and downloadable results in SQLite.
- Poll job progress using HTMX.
- Retain the existing Typer CLI.

## Expected music layout

```text
SOURCE/
    Artist Name/
        Album Name/
            01 Track.flac
            02 Track.mp3
            cover.jpg
```

## Selection file

```text
# Select every album by this artist
Pink Floyd

# Select individual albums
David Bowie/Low
Brian Eno/Another Green World
```

## Local development

Python 3.14 and FFmpeg are required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn music_to_mp3.web.main:app --reload
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Open `http://localhost:8000`.

## Synology and Dockhand deployment

1. Extract this project into a persistent directory or place it in Git.
2. Edit the host paths in `compose.yaml`.
3. Confirm the actual DSM USB mount path.
4. Create `.music-export-usb` in the root of the intended USB filesystem.
5. Deploy the Compose stack through Dockhand.
6. Open port 8787 through your existing reverse proxy.

The USB marker guard prevents the service from writing to the NAS mount-point
directory when the USB device is absent.

## Run with Compose

```bash
docker compose up -d --build
```

Open `http://NAS_ADDRESS:8787`.

## Configuration

Environment variables use the `MUSIC_EXPORT_` prefix:

- `MUSIC_EXPORT_SOURCE_ROOT`
- `MUSIC_EXPORT_DATA_ROOT`
- `MUSIC_EXPORT_DOWNLOAD_ROOT`
- `MUSIC_EXPORT_NAS_OUTPUT`
- `MUSIC_EXPORT_USB_OUTPUT`
- `MUSIC_EXPORT_USB_MARKER`
- `MUSIC_EXPORT_CONVERSION_WORKERS`
- `MUSIC_EXPORT_MAX_ACTIVE_JOBS`
- `MUSIC_EXPORT_DOWNLOAD_RETENTION_HOURS`
- `MUSIC_EXPORT_MAX_SELECTION_UPLOAD_BYTES`

## Important limitations of this first web release

- Authentication is not included. Put it behind an authenticated reverse proxy
  and do not expose it directly to the internet.
- The in-process job executor assumes one Uvicorn process. Do not add multiple
  Uvicorn workers. A later release can move jobs to a separate persistent worker.
- Cancellation stops scheduling useful work as futures complete, but FFmpeg
  processes already running are allowed to finish.
- Download cleanup runs on service startup. A scheduled cleanup task can be
  added later.
- HTMX is loaded from jsDelivr. Vendor the file under `static` if the NAS should
  work without internet access.

## Tests

```bash
pytest
ruff check .
mypy src
```
