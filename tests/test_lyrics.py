import io
import urllib.error

import pytest

from tunehound.lyrics import fetch_lyrics, lyrics_url
from tunehound.track import Track

TRACK = Track("A Song", ("Main", "Guest"), 213573, "x")

# Made-up text. A test never holds real lyrics.
MADE_UP = "first made-up line\nsecond made-up line"


def test_lyrics_url_names_the_artist_the_title_and_the_length():
    assert lyrics_url(TRACK) == (
        "https://lrclib.net/api/get?artist_name=Main&track_name=A+Song&duration=214"
    )


def test_lyrics_url_adds_the_album_when_there_is_one():
    track = Track("A Song", ("Main",), 1000, "x", album="An Album")
    assert "album_name=An+Album" in lyrics_url(track)


def test_fetch_lyrics_gives_the_plain_lyrics():
    answer = {"plainLyrics": f"  {MADE_UP}\n", "instrumental": False}
    assert fetch_lyrics(TRACK, lambda url: answer) == MADE_UP


def test_fetch_lyrics_gives_none_for_an_instrumental():
    answer = {"plainLyrics": None, "instrumental": True}
    assert fetch_lyrics(TRACK, lambda url: answer) is None


def test_fetch_lyrics_gives_none_for_empty_lyrics():
    assert fetch_lyrics(TRACK, lambda url: {"plainLyrics": "   "}) is None


def http_error(code):
    return urllib.error.HTTPError("https://lrclib.net", code, "x", {}, io.BytesIO())


def test_fetch_lyrics_gives_none_when_lrclib_has_no_lyrics():
    def get_json(url):
        raise http_error(404)

    assert fetch_lyrics(TRACK, get_json) is None


def test_fetch_lyrics_raises_other_http_errors():
    def get_json(url):
        raise http_error(500)

    with pytest.raises(urllib.error.HTTPError):
        fetch_lyrics(TRACK, get_json)
