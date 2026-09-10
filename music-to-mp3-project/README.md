# music-to-mp3

Copy existing MP3 files and convert selected FLAC files to MP3 while preserving
metadata and cover art. Artist and album selection is determined from the source
directory structure rather than audio tags.

## Expected source layout

```text
SOURCE/
    Artist Name/
        Album Name/
            01 Track.flac
            02 Track.mp3
            cover.jpg
```

The first directory beneath the source root is the artist. The second is the
album. Deeper directories are retained in the output path.

## Selection file

Use UTF-8 text with one selection per line. An artist selects all albums. An
`Artist/Album` entry selects one album. Empty lines and full-line comments are
ignored.

```text
# Complete artists
Pink Floyd
The Beatles

# Individual albums
David Bowie/Low
Brian Eno/Another Green World
```

## Install

Install FFmpeg separately and ensure `ffmpeg` is available on `PATH`.

```bash
python -m pip install .
```

For development tools:

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
music-to-mp3 SOURCE OUTPUT config/selections.txt
```

Useful options:

```bash
music-to-mp3 SOURCE OUTPUT selections.txt --workers 8 --quality 2 --overwrite
```

Run `music-to-mp3 --help` for the complete interface.

## Docker

```bash
docker compose run --rm music-to-mp3
```

Edit the volume paths and command in `compose.yaml` before running it.

## Tests and checks

```bash
pytest
ruff check .
mypy src
```
