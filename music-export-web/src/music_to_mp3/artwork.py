"""Locate external artwork and determine image types."""

from pathlib import Path

from music_to_mp3.constants import COVER_STEMS, IMAGE_SUFFIXES


def image_mime_type(path: Path) -> str:
    """Determine the MIME type of a supported cover image.

    Args:
        path: Image file to inspect.

    Returns:
        MIME type inferred from the file signature or suffix.
    """

    with path.open("rb") as image_file:
        signature = image_file.read(16)
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if signature.startswith(b"RIFF") and signature[8:12] == b"WEBP":
        return "image/webp"
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.casefold(), "application/octet-stream")


def find_cover_art(directory: Path) -> Path | None:
    """Find the most likely external front cover in a directory.

    Args:
        directory: Album directory containing an audio file.

    Returns:
        Preferred cover, the sole supported image, or None.
    """

    images = sorted(
        (
            entry
            for entry in directory.iterdir()
            if entry.is_file() and entry.suffix.casefold() in IMAGE_SUFFIXES
        ),
        key=lambda item: item.name.casefold(),
    )
    images_by_stem = {image.stem.casefold(): image for image in images}
    for preferred_stem in COVER_STEMS:
        if preferred_stem in images_by_stem:
            return images_by_stem[preferred_stem]
    return images[0] if len(images) == 1 else None
