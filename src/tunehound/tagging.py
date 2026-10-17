"""Write the metadata of a track into an audio file."""

from pathlib import Path

from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    TSRC,
    WOAS,
    ID3NoHeaderError,
)

from tunehound.track import Track


class TaggingError(Exception):
    """Tell that TuneHound cannot write tags into a file."""


def image_mime(data: bytes) -> str:
    """Return the media type of image data."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise TaggingError("the cover is not a JPEG or a PNG image")


def _write_id3(path: Path, track: Track, cover: bytes | None) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.setall("TIT2", [TIT2(encoding=3, text=track.title)])
    tags.setall("TPE1", [TPE1(encoding=3, text=list(track.artists))])
    tags.setall("TPE2", [TPE2(encoding=3, text=track.artists[0])])
    tags.setall("WOAS", [WOAS(url=track.source_url)])
    if track.album:
        tags.setall("TALB", [TALB(encoding=3, text=track.album)])
    if track.release_date:
        tags.setall("TDRC", [TDRC(encoding=3, text=track.release_date)])
    if track.track_number:
        tags.setall("TRCK", [TRCK(encoding=3, text=str(track.track_number))])
    if track.disc_number:
        tags.setall("TPOS", [TPOS(encoding=3, text=str(track.disc_number))])
    if track.isrc:
        tags.setall("TSRC", [TSRC(encoding=3, text=track.isrc)])
    if cover is not None:
        tags.setall(
            "APIC",
            [
                APIC(
                    encoding=3, mime=image_mime(cover), type=3, desc="Cover", data=cover
                )
            ],
        )
    tags.save(path, v2_version=4)


_WRITERS = {".mp3": _write_id3}


def write_tags(path: Path, track: Track, cover: bytes | None = None) -> None:
    """Write the tags of a track, and the cover if there is one, into a file."""
    writer = _WRITERS.get(path.suffix.lower())
    if writer is None:
        raise TaggingError(f"TuneHound cannot tag {path.suffix} files")
    writer(path, track, cover)
