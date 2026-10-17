import pytest

from tunehound.providers.deezer import (
    DeezerError,
    DeezerProvider,
    fetch_list,
    fetch_track,
    parse_link,
    parse_track,
)


def make_track(**changes):
    data = {
        "id": 42,
        "type": "track",
        "title": "A Song",
        "duration": 211,
        "track_position": 3,
        "disk_number": 2,
        "release_date": "2004-01-12",
        "isrc": "GBXXX0000001",
        "explicit_lyrics": True,
        "artist": {"name": "Main"},
        "contributors": [{"name": "Main"}, {"name": "Guest"}, {"name": "Main"}],
        "album": {"title": "An Album", "cover_xl": "https://img.invalid/1000"},
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    ("link", "kind", "item_id"),
    [
        ("https://www.deezer.com/track/42", "track", "42"),
        ("https://www.deezer.com/en/album/7?utm=x", "album", "7"),
        ("https://deezer.com/pt-br/playlist/99", "playlist", "99"),
    ],
)
def test_parse_link_gives_the_kind_and_the_id(link, kind, item_id):
    assert parse_link(link) == (kind, item_id)


@pytest.mark.parametrize(
    "link", ["https://www.deezer.com/artist/1", "https://example.com/track/1", ""]
)
def test_parse_link_refuses_other_links(link):
    with pytest.raises(DeezerError):
        parse_link(link)


def test_parse_track_reads_all_fields():
    track = parse_track(make_track())
    assert track.title == "A Song"
    assert track.artists == ("Main", "Guest")
    assert track.duration_ms == 211000
    assert track.album == "An Album"
    assert track.track_number == 3
    assert track.disc_number == 2
    assert track.release_date == "2004-01-12"
    assert track.isrc == "GBXXX0000001"
    assert track.cover_url == "https://img.invalid/1000"
    assert track.explicit is True
    assert track.source_url == "https://www.deezer.com/track/42"


def test_parse_track_uses_the_artist_without_contributors():
    track = parse_track(make_track(contributors=[]))
    assert track.artists == ("Main",)


def test_parse_track_refuses_a_track_with_no_title():
    with pytest.raises(DeezerError):
        parse_track(make_track(title=""))


def test_fetch_track_asks_the_api():
    asked = []

    def get_json(url):
        asked.append(url)
        return make_track()

    assert fetch_track("https://www.deezer.com/fr/track/42", get_json).title == "A Song"
    assert asked == ["https://api.deezer.com/track/42"]


def test_fetch_track_reports_an_api_error():
    def get_json(url):
        return {"error": {"type": "DataException", "message": "no data", "code": 800}}

    with pytest.raises(DeezerError, match="no data"):
        fetch_track("https://www.deezer.com/track/0", get_json)


def test_fetch_list_follows_the_pages():
    pages = {
        "https://api.deezer.com/album/7": {"title": "An Album"},
        "https://api.deezer.com/album/7/tracks?limit=100": {
            "data": [{"id": 1, "type": "track"}, {"id": 2, "type": "track"}],
            "next": "https://api.deezer.com/album/7/tracks?limit=100&index=100",
        },
        "https://api.deezer.com/album/7/tracks?limit=100&index=100": {
            "data": [{"id": 3, "type": "track"}, {"id": 4, "type": "episode"}],
        },
    }
    found = fetch_list("https://www.deezer.com/album/7", pages.__getitem__)
    assert found.kind == "album"
    assert found.album == "An Album"
    assert found.track_links == (
        "https://www.deezer.com/track/1",
        "https://www.deezer.com/track/2",
        "https://www.deezer.com/track/3",
    )
    assert found.maybe_cut is False


def test_fetch_list_refuses_a_track_link():
    with pytest.raises(DeezerError):
        fetch_list("https://www.deezer.com/track/1", lambda url: {})


def test_provider_follows_a_short_link():
    asked = []
    provider = DeezerProvider(
        get_json=lambda url: asked.append(url) or make_track(),
        final_url=lambda url: "https://www.deezer.com/en/track/42",
    )
    short = "https://link.deezer.com/s/abc123"
    assert provider.owns(short)
    assert provider.kind_of(short) == "track"
    assert provider.fetch_track(short).title == "A Song"
    assert asked == ["https://api.deezer.com/track/42"]


def test_provider_owns_only_deezer_links():
    provider = DeezerProvider()
    assert provider.owns("https://www.deezer.com/album/7")
    assert not provider.owns("https://open.spotify.com/track/" + "a" * 22)
