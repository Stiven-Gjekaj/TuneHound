import pytest

from tunehound.providers.apple import (
    AppleMusicError,
    AppleMusicProvider,
    fetch_list,
    fetch_track,
    parse_link,
    parse_song,
)


def make_song(**changes):
    data = {
        "wrapperType": "track",
        "kind": "song",
        "trackId": 11,
        "trackName": "A Song",
        "artistName": "Main",
        "collectionName": "An Album",
        "trackNumber": 4,
        "discNumber": 2,
        "releaseDate": "1987-01-01T12:00:00Z",
        "trackTimeMillis": 214720,
        "artworkUrl100": "https://img.invalid/a/100x100bb.jpg",
        "trackExplicitness": "explicit",
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    ("link", "parsed"),
    [
        ("https://music.apple.com/us/song/a-song/11", ("track", "11", "us")),
        ("https://music.apple.com/gb/song/11", ("track", "11", "gb")),
        ("https://music.apple.com/us/album/an-album/7?i=11", ("track", "11", "us")),
        (
            "https://music.apple.com/us/album/an-album/7?l=en&i=11",
            ("track", "11", "us"),
        ),
        ("https://music.apple.com/de/album/an-album/7", ("album", "7", "de")),
        ("https://music.apple.com/de/album/7?l=en", ("album", "7", "de")),
        ("https://geo.music.apple.com/us/album/x/7", ("album", "7", "us")),
    ],
)
def test_parse_link_gives_the_kind_the_id_and_the_country(link, parsed):
    assert parse_link(link) == parsed


@pytest.mark.parametrize(
    "link",
    [
        "https://music.apple.com/us/playlist/mix/pl.abc",
        "https://music.apple.com/us/artist/main/5",
        "https://example.com/us/song/11",
    ],
)
def test_parse_link_refuses_other_links(link):
    with pytest.raises(AppleMusicError):
        parse_link(link)


def test_parse_song_reads_all_fields():
    track = parse_song(make_song(), "us")
    assert track.title == "A Song"
    assert track.artists == ("Main",)
    assert track.duration_ms == 214720
    assert track.album == "An Album"
    assert (track.track_number, track.disc_number) == (4, 2)
    assert track.release_date == "1987-01-01"
    assert track.cover_url == "https://img.invalid/a/1000x1000bb.jpg"
    assert track.explicit is True
    assert track.source_url == "https://music.apple.com/us/song/11"


def test_parse_song_refuses_an_item_that_is_not_a_song():
    with pytest.raises(AppleMusicError):
        parse_song(make_song(kind="music-video"), "us")


def test_fetch_track_asks_the_lookup_api_with_the_country():
    asked = []

    def get_json(url):
        asked.append(url)
        return {"resultCount": 1, "results": [make_song()]}

    fetch_track("https://music.apple.com/gb/album/x/7?i=11", get_json)
    assert asked == ["https://itunes.apple.com/lookup?id=11&country=gb"]


def test_fetch_track_reports_a_missing_song():
    with pytest.raises(AppleMusicError, match="no song"):
        fetch_track("https://music.apple.com/us/song/0", lambda url: {"results": []})


def test_fetch_list_orders_the_songs_by_disc_and_number():
    answer = {
        "results": [
            {"wrapperType": "collection", "collectionName": "An Album"},
            make_song(trackId=3, discNumber=2, trackNumber=1),
            make_song(trackId=2, discNumber=1, trackNumber=2),
            make_song(trackId=1, discNumber=1, trackNumber=1),
        ]
    }
    asked = []
    found = fetch_list(
        "https://music.apple.com/us/album/an-album/7",
        lambda url: asked.append(url) or answer,
    )
    assert asked == ["https://itunes.apple.com/lookup?id=7&country=us&entity=song"]
    assert found.album == "An Album"
    assert found.track_links == (
        "https://music.apple.com/us/song/1",
        "https://music.apple.com/us/song/2",
        "https://music.apple.com/us/song/3",
    )


def test_fetch_list_reports_a_missing_album():
    with pytest.raises(AppleMusicError, match="no album"):
        fetch_list("https://music.apple.com/us/album/x/7", lambda url: {"results": []})


def test_provider_owns_only_apple_music_links():
    provider = AppleMusicProvider()
    assert provider.owns("https://music.apple.com/us/album/x/7")
    assert provider.kind_of("https://music.apple.com/us/album/x/7?i=1") == "track"
    assert not provider.owns("https://www.deezer.com/track/1")
