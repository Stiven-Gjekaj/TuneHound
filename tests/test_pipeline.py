from pathlib import Path

import pytest

from tunehound.matching import Candidate
from tunehound.pipeline import NoMatchError, download_track, safe_filename
from tunehound.track import Track

TRACK = Track(
    title="Song: Part 1/2",
    artists=("First",),
    duration_ms=200000,
    source_url="https://open.spotify.com/track/x",
    cover_url="https://img.invalid/640",
)
GOOD = Candidate("good", "First - Song: Part 1/2", "First - Topic", 200.0, "youtube")
BAD = Candidate("bad", "Other Thing", "Someone", 200.0, "youtube")


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("AC/DC - Back In Black", "AC_DC - Back In Black"),
        ('What? "Yes" <No> | a*b \\ c:d', "What_ _Yes_ _No_ _ a_b _ c_d"),
        ("  lots   of\tspace  ", "lots of space"),
        ("ends with dots...", "ends with dots"),
        ("...", "track"),
        ("a" * 300, "a" * 200),
    ],
)
def test_safe_filename_removes_unsafe_characters(text, name):
    assert safe_filename(text) == name


def make_steps(candidates, cover=b"\xff\xd8\xffcover", cover_error=None):
    calls = {}

    def fetch(link):
        calls["link"] = link
        return TRACK

    def search(track):
        return candidates

    def download(url, stem, cookies_from_browser=None):
        calls["download"] = (url, stem, cookies_from_browser)
        return stem.with_name(stem.name + ".mp3")

    def get_bytes(url):
        calls["cover_url"] = url
        if cover_error:
            raise cover_error
        return cover

    def tag(path, track, cover_data):
        calls["tag"] = (path, track, cover_data)

    steps = {
        "fetch": fetch,
        "search": search,
        "download": download,
        "get_bytes": get_bytes,
        "tag": tag,
    }
    return steps, calls


def test_download_track_runs_all_steps_in_order(tmp_path):
    steps, calls = make_steps([BAD, GOOD])
    result = download_track("link", tmp_path, cookies_from_browser="firefox", **steps)

    stem = tmp_path / "First - Song_ Part 1_2"
    assert calls["link"] == "link"
    assert calls["download"] == (GOOD.url, stem, "firefox")
    assert calls["cover_url"] == "https://img.invalid/640"
    assert calls["tag"] == (Path(f"{stem}.mp3"), TRACK, b"\xff\xd8\xffcover")
    assert result.match == GOOD
    assert result.path == Path(f"{stem}.mp3")


def test_download_track_fails_when_nothing_matches(tmp_path):
    steps, calls = make_steps([BAD])
    with pytest.raises(NoMatchError):
        download_track("link", tmp_path, **steps)
    assert "download" not in calls


def test_download_track_tags_without_a_cover_when_the_cover_fails(tmp_path):
    steps, calls = make_steps([GOOD], cover_error=OSError("offline"))
    download_track("link", tmp_path, **steps)
    assert calls["tag"][2] is None
