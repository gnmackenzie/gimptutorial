"""Translate FLAC metadata and artwork into ID3v2.4 frames."""

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    APIC, COMM, ID3, ID3NoHeaderError, TALB, TBPM, TCOM, TCON, TCOP,
    TDRC, TENC, TEXT, TIT2, TKEY, TLAN, TMED, TOAL, TOPE, TPE1, TPE2,
    TPE3, TPOS, TPUB, TRCK, TSRC, TSSE, TSST, TSO2, TSOA, TSOC, TSOP,
    TSOT, TXXX, USLT,
)
from mutagen.id3._frames import TextFrame

from music_to_mp3.artwork import image_mime_type

TEXT_FRAME_MAP: Final[dict[str, type[TextFrame]]] = {
    "album": TALB,
    "albumartist": TPE2,
    "albumartistsort": TSO2,
    "albumsort": TSOA,
    "artist": TPE1,
    "artistsort": TSOP,
    "bpm": TBPM,
    "composer": TCOM,
    "composersort": TSOC,
    "copyright": TCOP,
    "date": TDRC,
    "discnumber": TPOS,
    "encodedby": TENC,
    "encoder": TSSE,
    "genre": TCON,
    "initialkey": TKEY,
    "isrc": TSRC,
    "language": TLAN,
    "lyricist": TEXT,
    "media": TMED,
    "originalalbum": TOAL,
    "originalartist": TOPE,
    "performer": TPE3,
    "publisher": TPUB,
    "subtitle": TSST,
    "title": TIT2,
    "titlesort": TSOT,
    "tracknumber": TRCK,
    "year": TDRC,
}


def normalise_tag_name(name: str) -> str:
    """Normalise a Vorbis comment name for ID3 mapping.

    Args:
        name: Vorbis comment field name.

    Returns:
        Case-folded field name containing only alphanumeric characters.
    """

    return "".join(character for character in name.casefold() if character.isalnum())


def values_as_text(values: Iterable[object]) -> list[str]:
    """Convert metadata values to non-empty text.

    Args:
        values: Values obtained from a Mutagen tag collection.

    Returns:
        Non-empty string values in their original order.
    """

    return [text for value in values if (text := str(value).strip())]


def add_text_metadata(tags: ID3, key: str, values: Sequence[str]) -> None:
    """Translate one FLAC Vorbis comment into ID3 metadata.

    Args:
        tags: Destination ID3 tag collection.
        key: Original Vorbis comment field name.
        values: Text values for the field.
    """

    if not values:
        return
    normalised_key = normalise_tag_name(key)
    if normalised_key in {"comment", "description"}:
        for index, value in enumerate(values):
            description = key if index == 0 else f"{key} {index + 1}"
            tags.add(COMM(encoding=3, lang="eng", desc=description, text=value))
        return
    if normalised_key in {"lyrics", "unsyncedlyrics"}:
        for index, value in enumerate(values):
            description = "" if index == 0 else str(index + 1)
            tags.add(USLT(encoding=3, lang="eng", desc=description, text=value))
        return
    frame_class = TEXT_FRAME_MAP.get(normalised_key)
    if frame_class is not None:
        tags.add(frame_class(encoding=3, text=list(values)))
    else:
        tags.add(TXXX(encoding=3, desc=key, text=list(values)))


def add_picture(tags: ID3, picture: Picture, description: str) -> None:
    """Copy a FLAC picture into an ID3 APIC frame.

    Args:
        tags: Destination ID3 tag collection.
        picture: Picture read from the FLAC metadata.
        description: Picture description.
    """

    tags.add(
        APIC(
            encoding=3,
            mime=picture.mime or "application/octet-stream",
            type=picture.type,
            desc=description,
            data=picture.data,
        )
    )


def copy_flac_metadata(
    source: Path,
    destination: Path,
    external_cover: Path | None,
) -> None:
    """Copy FLAC metadata and artwork into an MP3 ID3v2.4 tag.

    Args:
        source: Source FLAC file.
        destination: Newly encoded MP3 file.
        external_cover: Optional external front-cover image.
    """

    flac = FLAC(source)
    try:
        tags = ID3(destination)
        tags.clear()
    except ID3NoHeaderError:
        tags = ID3()

    if flac.tags is not None:
        for key, raw_values in flac.tags.items():
            add_text_metadata(tags, key, values_as_text(raw_values))

    for index, picture in enumerate(flac.pictures):
        if external_cover is not None and picture.type == 3:
            continue
        add_picture(tags, picture, picture.desc or f"Embedded picture {index + 1}")

    if external_cover is not None:
        tags.add(
            APIC(
                encoding=3,
                mime=image_mime_type(external_cover),
                type=3,
                desc="Cover (front)",
                data=external_cover.read_bytes(),
            )
        )
    tags.save(destination, v2_version=4, v1=0)
