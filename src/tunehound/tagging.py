"""Write the metadata of a track into an audio file."""

import base64
from pathlib import Path

from mutagen.flac import FLAC, Picture
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
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
from mutagen.oggopus import OggOpus

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


def _write_mp4(path: Path, track: Track, cover: bytes | None) -> None:
    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    tags["\xa9nam"] = [track.title]
    tags["\xa9ART"] = list(track.artists)
    tags["aART"] = [track.artists[0]]
    if track.album:
        tags["\xa9alb"] = [track.album]
    if track.release_date:
        tags["\xa9day"] = [track.release_date]
    if track.track_number:
        tags["trkn"] = [(track.track_number, 0)]
    if track.disc_number:
        tags["disk"] = [(track.disc_number, 0)]
    if track.isrc:
        tags["----:com.apple.iTunes:ISRC"] = [MP4FreeForm(track.isrc.encode())]
    tags["----:com.apple.iTunes:SOURCE"] = [MP4FreeForm(track.source_url.encode())]
    if cover is not None:
        kind = (
            MP4Cover.FORMAT_PNG
            if image_mime(cover) == "image/png"
            else MP4Cover.FORMAT_JPEG
        )
        tags["covr"] = [MP4Cover(cover, imageformat=kind)]
    audio.save()


def _vorbis_fields(track: Track) -> dict[str, list[str]]:
    fields = {
        "title": [track.title],
        "artist": list(track.artists),
        "albumartist": [track.artists[0]],
        "website": [track.source_url],
    }
    if track.album:
        fields["album"] = [track.album]
    if track.release_date:
        fields["date"] = [track.release_date]
    if track.track_number:
        fields["tracknumber"] = [str(track.track_number)]
    if track.disc_number:
        fields["discnumber"] = [str(track.disc_number)]
    if track.isrc:
        fields["isrc"] = [track.isrc]
    return fields


def _picture(cover: bytes) -> Picture:
    picture = Picture()
    picture.type = 3
    picture.mime = image_mime(cover)
    picture.desc = "Cover"
    picture.data = cover
    return picture


def _write_flac(path: Path, track: Track, cover: bytes | None) -> None:
    audio = FLAC(path)
    for key, values in _vorbis_fields(track).items():
        audio[key] = values
    if cover is not None:
        audio.clear_pictures()
        audio.add_picture(_picture(cover))
    audio.save()


def _write_opus(path: Path, track: Track, cover: bytes | None) -> None:
    audio = OggOpus(path)
    for key, values in _vorbis_fields(track).items():
        audio[key] = values
    if cover is not None:
        # Ogg files keep the cover as a FLAC picture block in base64.
        block = base64.b64encode(_picture(cover).write()).decode("ascii")
        audio["metadata_block_picture"] = [block]
    audio.save()


_WRITERS = {
    ".mp3": _write_id3,
    ".m4a": _write_mp4,
    ".flac": _write_flac,
    ".opus": _write_opus,
}


def write_tags(path: Path, track: Track, cover: bytes | None = None) -> None:
    """Write the tags of a track, and the cover if there is one, into a file."""
    writer = _WRITERS.get(path.suffix.lower())
    if writer is None:
        raise TaggingError(f"TuneHound cannot tag {path.suffix} files")
    writer(path, track, cover)
