import pytest

from tunehound.providers.direct import (
    DirectError,
    DirectProvider,
    link_kind,
    parse_info,
)


@pytest.mark.parametrize(
    ("link", "kind"),
    [
        ("https://www.youtube.com/watch?v=abc", "track"),
        ("https://music.youtube.com/watch?v=abc&list=RD1", "track"),
        ("https://youtu.be/abc", "track"),
        ("https://www.youtube.com/shorts/abc", "track"),
        ("https://www.youtube.com/playlist?list=PL1", "playlist"),
        ("https://music.youtube.com/playlist?list=OLAK1", "playlist"),
        ("https://soundcloud.com/artist/song", "track"),
        ("https://soundcloud.com/artist/sets/mix", "playlist"),
        ("https://api.soundcloud.com/tracks/soundcloud%3Atracks%3A1", "track"),
        ("https://artist.bandcamp.com/track/song", "track"),
        ("https://artist.bandcamp.com/album/record", "album"),
    ],
)
def test_link_kind_knows_the_direct_links(link, kind):
    assert link_kind(link) == kind


@pytest.mark.parametrize(
    "link",
    [
        "https://www.youtube.com/@channel",
        "https://youtu.be/",
        "https://soundcloud.com/artist",
        "https://artist.bandcamp.com/",
        "https://open.spotify.com/track/abc",
        "plain text",
    ],
)
def test_link_kind_refuses_other_links(link):
    assert link_kind(link) is None


def make_info(**changes):
    info = {
        "title": "Main - A Song (Official Video)",
        "uploader": "Main",
        "duration": 213.4,
        "upload_date": "20091025",
        "webpage_url": "https://www.youtube.com/watch?v=abc",
        "thumbnails": [
            {"url": "https://i.invalid/small.jpg", "width": 120, "height": 90},
            {"url": "https://i.invalid/big.webp", "width": 1920, "height": 1080},
            {"url": "https://i.invalid/big.jpg?x=1", "width": 1280, "height": 720},
        ],
    }
    info.update(changes)
    return info


def test_parse_info_uses_the_uploader_and_removes_the_artist_from_the_title():
    track = parse_info(make_info(), "link")
    assert track.artists == ("Main",)
    assert track.title == "A Song (Official Video)"
    assert track.duration_ms == 213400
    assert track.release_date == "2009-10-25"
    assert track.source_url == "https://www.youtube.com/watch?v=abc"


def test_parse_info_takes_the_largest_jpeg_or_png_cover():
    assert parse_info(make_info(), "link").cover_url == "https://i.invalid/big.jpg?x=1"


def test_parse_info_gives_no_cover_when_there_is_only_webp():
    info = make_info(
        thumbnails=[{"url": "https://i.invalid/a.webp"}],
        thumbnail="https://i.invalid/a.webp",
    )
    assert parse_info(info, "link").cover_url is None


def test_parse_info_prefers_the_music_fields():
    info = make_info(
        track="Real Title",
        artists=["One", "Two"],
        album="Record",
        track_number=5,
        release_date="20200102",
    )
    track = parse_info(info, "link")
    assert (track.title, track.artists, track.album) == (
        "Real Title",
        ("One", "Two"),
        "Record",
    )
    assert track.track_number == 5
    assert track.release_date == "2020-01-02"


def test_parse_info_has_defaults_for_missing_fields():
    track = parse_info({}, " https://x.invalid/a ")
    assert track.artists == ("Unknown Artist",)
    assert track.title == "Unknown Title"
    assert track.source_url == "https://x.invalid/a"


def test_provider_reads_a_track_without_the_playlist():
    asked = []
    provider = DirectProvider(
        lambda link, flat: asked.append((link, flat)) or make_info()
    )
    assert provider.direct is True
    assert (
        provider.fetch_track("https://youtu.be/abc").title == "A Song (Official Video)"
    )
    assert asked == [("https://youtu.be/abc", False)]


def test_provider_reads_the_entries_of_a_list():
    info = {
        "title": "Record",
        "entries": [
            {"url": "https://artist.bandcamp.com/track/one"},
            None,
            {"url": "abc", "ie_key": "Youtube"},
            {"title": "no url"},
        ],
    }
    provider = DirectProvider(lambda link, flat: info)
    found = provider.fetch_list("https://artist.bandcamp.com/album/record")
    assert found.kind == "album"
    assert found.album == "Record"
    assert found.track_links == (
        "https://artist.bandcamp.com/track/one",
        "https://www.youtube.com/watch?v=abc",
    )


def test_provider_refuses_an_unknown_link():
    with pytest.raises(DirectError):
        DirectProvider().kind_of("https://example.com/x")
