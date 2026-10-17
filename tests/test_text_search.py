import pytest

from tunehound.providers.text import SearchError, TextSearchProvider


def deezer_track(track_id):
    return {
        "id": track_id,
        "title": "A Song",
        "duration": 200,
        "artist": {"name": "Main"},
        "album": {"title": "An Album"},
    }


@pytest.mark.parametrize("text", ["main a song", "  Main - A Song  ", "beyonce halo"])
def test_owns_a_plain_text(text):
    assert TextSearchProvider().owns(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "https://example.com/x",
        "HTTP://X.COM",
        "spotify:track:abc",
        "ftp://x",
    ],
)
def test_does_not_own_a_link_or_an_empty_text(text):
    assert not TextSearchProvider().owns(text)


def test_fetch_track_takes_the_first_result_and_reads_the_full_track():
    asked = []

    def get_json(url):
        asked.append(url)
        if "search" in url:
            return {"data": [{"id": 5}, {"id": 6}], "total": 2}
        return deezer_track(5)

    track = TextSearchProvider(get_json).fetch_track("  Main -  A Song ")
    assert asked == [
        "https://api.deezer.com/search?q=Main%20-%20A%20Song&limit=1",
        "https://api.deezer.com/track/5",
    ]
    assert track.album == "An Album"
    assert track.source_url == "https://www.deezer.com/track/5"


def test_fetch_track_reports_no_result():
    provider = TextSearchProvider(lambda url: {"data": [], "total": 0})
    with pytest.raises(SearchError, match="found no song for: nothing here"):
        provider.fetch_track("nothing here")


def test_kind_is_always_track():
    assert TextSearchProvider().kind_of("anything") == "track"
