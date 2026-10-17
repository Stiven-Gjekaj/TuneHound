import shutil
import subprocess

import pytest
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from tunehound.tagging import TaggingError, image_mime, write_tags
from tunehound.track import Track

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16

TRACK = Track(
    title="A Song",
    artists=("First", "Second"),
    duration_ms=1000,
    source_url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
    album="An Album",
    track_number=7,
    disc_number=2,
    release_date="1987-11-12",
    isrc="GBARL9300135",
)


def make_silent(tmp_path, suffix, codec_args):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not on the PATH")
    path = tmp_path / f"silent{suffix}"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "1",
        ]
        + codec_args
        + [str(path)],
        check=True,
    )
    return path


@pytest.fixture
def silent_flac(tmp_path):
    return make_silent(tmp_path, ".flac", ["-c:a", "flac"])


@pytest.fixture
def silent_opus(tmp_path):
    return make_silent(tmp_path, ".opus", ["-c:a", "libopus"])


@pytest.fixture
def silent_m4a(tmp_path):
    return make_silent(tmp_path, ".m4a", ["-c:a", "aac"])


@pytest.fixture
def silent_mp3(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not on the PATH")
    path = tmp_path / "silent.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "1",
            "-q:a",
            "9",
            str(path),
        ],
        check=True,
    )
    return path


def test_image_mime_knows_png_and_jpeg():
    assert image_mime(PNG) == "image/png"
    assert image_mime(JPEG) == "image/jpeg"


def test_image_mime_refuses_other_data():
    with pytest.raises(TaggingError):
        image_mime(b"GIF89a")


def test_write_tags_writes_the_metadata(silent_mp3):
    write_tags(silent_mp3, TRACK, cover=JPEG)
    tags = ID3(silent_mp3)
    assert tags["TIT2"].text == ["A Song"]
    assert tags["TPE1"].text == ["First", "Second"]
    assert tags["TPE2"].text == ["First"]
    assert tags["TALB"].text == ["An Album"]
    assert tags["TRCK"].text == ["7"]
    assert tags["TPOS"].text == ["2"]
    assert str(tags["TDRC"].text[0]) == "1987-11-12"
    assert tags["TSRC"].text == ["GBARL9300135"]
    assert tags["WOAS"].url == TRACK.source_url
    [cover] = tags.getall("APIC")
    assert (cover.mime, cover.type, cover.data) == ("image/jpeg", 3, JPEG)
    assert tags.version == (2, 4, 0)


def test_write_tags_keeps_the_audio_playable(silent_mp3):
    write_tags(silent_mp3, TRACK, cover=PNG)
    assert MP3(silent_mp3).info.length == pytest.approx(1.0, abs=0.1)


def test_write_tags_leaves_out_the_missing_fields(silent_mp3):
    bare = Track(
        title="T", artists=("A",), duration_ms=1, source_url="https://x.invalid"
    )
    write_tags(silent_mp3, bare)
    tags = ID3(silent_mp3)
    for frame in ("TALB", "TRCK", "TPOS", "TDRC", "TSRC", "APIC"):
        assert not tags.getall(frame)


def test_write_tags_replaces_the_old_tags(silent_mp3):
    write_tags(silent_mp3, TRACK, cover=JPEG)
    write_tags(silent_mp3, TRACK, cover=PNG)
    assert len(ID3(silent_mp3).getall("APIC")) == 1
    assert ID3(silent_mp3).getall("APIC")[0].mime == "image/png"


def test_write_tags_refuses_an_unknown_format(tmp_path):
    with pytest.raises(TaggingError):
        write_tags(tmp_path / "song.wav", TRACK)


def test_write_tags_writes_the_metadata_into_m4a(silent_m4a):
    from mutagen.mp4 import MP4, MP4Cover

    write_tags(silent_m4a, TRACK, cover=PNG)
    tags = MP4(silent_m4a).tags
    assert tags["\xa9nam"] == ["A Song"]
    assert tags["\xa9ART"] == ["First", "Second"]
    assert tags["aART"] == ["First"]
    assert tags["\xa9alb"] == ["An Album"]
    assert tags["\xa9day"] == ["1987-11-12"]
    assert tags["trkn"] == [(7, 0)]
    assert tags["disk"] == [(2, 0)]
    assert bytes(tags["----:com.apple.iTunes:ISRC"][0]) == b"GBARL9300135"
    [cover] = tags["covr"]
    assert bytes(cover) == PNG
    assert cover.imageformat == MP4Cover.FORMAT_PNG


def test_write_tags_keeps_the_m4a_audio_playable(silent_m4a):
    from mutagen.mp4 import MP4

    write_tags(silent_m4a, TRACK, cover=JPEG)
    assert MP4(silent_m4a).info.length == pytest.approx(1.0, abs=0.1)


def check_vorbis_fields(tags):
    assert tags["title"] == ["A Song"]
    assert tags["artist"] == ["First", "Second"]
    assert tags["albumartist"] == ["First"]
    assert tags["album"] == ["An Album"]
    assert tags["date"] == ["1987-11-12"]
    assert tags["tracknumber"] == ["7"]
    assert tags["discnumber"] == ["2"]
    assert tags["isrc"] == ["GBARL9300135"]
    assert tags["website"] == [TRACK.source_url]


def test_write_tags_writes_the_metadata_into_flac(silent_flac):
    from mutagen.flac import FLAC

    write_tags(silent_flac, TRACK, cover=JPEG)
    write_tags(silent_flac, TRACK, cover=PNG)
    audio = FLAC(silent_flac)
    check_vorbis_fields(audio)
    [picture] = audio.pictures
    assert (picture.mime, picture.type, picture.data) == ("image/png", 3, PNG)
    assert audio.info.length == pytest.approx(1.0, abs=0.1)


def test_write_tags_writes_the_metadata_into_opus(silent_opus):
    import base64

    from mutagen.flac import Picture
    from mutagen.oggopus import OggOpus

    write_tags(silent_opus, TRACK, cover=JPEG)
    audio = OggOpus(silent_opus)
    check_vorbis_fields(audio)
    [block] = audio["metadata_block_picture"]
    picture = Picture(base64.b64decode(block))
    assert (picture.mime, picture.type, picture.data) == ("image/jpeg", 3, JPEG)
    assert audio.info.length == pytest.approx(1.0, abs=0.1)
