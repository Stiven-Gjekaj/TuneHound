import json

import pytest

from tunehound.providers.spotify import (
    SpotifyError,
    SpotifyLink,
    TrackList,
    fetch_list,
    fetch_track,
    parse_embed_list,
    parse_embed_page,
    parse_link,
    parse_track_id,
)

TRACK_ID = "4uLU6hMCjMI75M1A2tKUQC"


@pytest.mark.parametrize(
    "link",
    [
        f"https://open.spotify.com/track/{TRACK_ID}",
        f"https://open.spotify.com/track/{TRACK_ID}?si=abc123",
        f"https://open.spotify.com/intl-de/track/{TRACK_ID}",
        f"https://open.spotify.com/intl-pt-br/track/{TRACK_ID}",
        f"https://open.spotify.com/embed/track/{TRACK_ID}",
        f"http://open.spotify.com/track/{TRACK_ID}/",
        f"  spotify:track:{TRACK_ID}  ",
    ],
)
def test_parse_track_id_accepts_track_links(link):
    assert parse_track_id(link) == TRACK_ID


@pytest.mark.parametrize(
    ("link", "kind"),
    [
        (f"https://open.spotify.com/track/{TRACK_ID}", "track"),
        (f"https://open.spotify.com/intl-fr/album/{TRACK_ID}?si=1", "album"),
        (f"https://open.spotify.com/embed/playlist/{TRACK_ID}", "playlist"),
        (f"spotify:album:{TRACK_ID}", "album"),
        (f"spotify:playlist:{TRACK_ID}", "playlist"),
    ],
)
def test_parse_link_gives_the_kind_and_the_id(link, kind):
    assert parse_link(link) == SpotifyLink(kind=kind, id=TRACK_ID)


@pytest.mark.parametrize(
    "link",
    [
        f"https://open.spotify.com/artist/{TRACK_ID}",
        f"spotify:episode:{TRACK_ID}",
        "https://open.spotify.com/album/short",
        "",
    ],
)
def test_parse_link_refuses_other_links(link):
    with pytest.raises(SpotifyError):
        parse_link(link)


@pytest.mark.parametrize(
    "link",
    [
        f"https://open.spotify.com/album/{TRACK_ID}",
        f"https://open.spotify.com/playlist/{TRACK_ID}",
        f"spotify:album:{TRACK_ID}",
        "https://open.spotify.com/track/short",
        f"https://example.com/track/{TRACK_ID}",
        "",
    ],
)
def test_parse_track_id_refuses_other_links(link):
    with pytest.raises(SpotifyError):
        parse_track_id(link)


def make_entity(**changes):
    entity = {
        "type": "track",
        "name": "A Song",
        "artists": [{"name": "First"}, {"name": "Second"}],
        "duration": 213573,
        "isExplicit": True,
        "releaseDate": {"isoString": "1987-11-12T00:00:00Z"},
        "visualIdentity": {
            "image": [
                {"url": "https://img.invalid/300", "maxWidth": 300},
                {"url": "https://img.invalid/640", "maxWidth": 640},
                {"url": "https://img.invalid/64", "maxWidth": 64},
            ]
        },
    }
    entity.update(changes)
    return entity


def make_page(entity):
    data = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(data)}"
        "</script></body></html>"
    )


def test_parse_embed_page_reads_the_metadata():
    track = parse_embed_page(make_page(make_entity()), TRACK_ID)
    assert track.title == "A Song"
    assert track.artists == ("First", "Second")
    assert track.duration_ms == 213573
    assert track.release_date == "1987-11-12"
    assert track.explicit is True
    assert track.source_url == f"https://open.spotify.com/track/{TRACK_ID}"


def test_parse_embed_page_takes_the_largest_cover():
    track = parse_embed_page(make_page(make_entity()), TRACK_ID)
    assert track.cover_url == "https://img.invalid/640"


def test_parse_embed_page_accepts_missing_optional_fields():
    entity = make_entity()
    del entity["releaseDate"], entity["visualIdentity"], entity["isExplicit"]
    track = parse_embed_page(make_page(entity), TRACK_ID)
    assert track.release_date is None
    assert track.cover_url is None
    assert track.explicit is False


@pytest.mark.parametrize(
    "page",
    [
        "<html>no data</html>",
        '<script id="__NEXT_DATA__" type="application/json">{bad</script>',
        '<script id="__NEXT_DATA__" type="application/json">{}</script>',
        make_page(make_entity(type="episode")),
        make_page(make_entity(artists=[])),
        make_page(make_entity(name="")),
    ],
)
def test_parse_embed_page_refuses_a_bad_page(page):
    with pytest.raises(SpotifyError):
        parse_embed_page(page, TRACK_ID)


def test_fetch_track_reads_the_embed_page_of_the_link():
    asked = []

    def get_text(url):
        asked.append(url)
        return make_page(make_entity())

    track = fetch_track(f"https://open.spotify.com/track/{TRACK_ID}?si=x", get_text)
    assert asked == [f"https://open.spotify.com/embed/track/{TRACK_ID}"]
    assert track.title == "A Song"


OTHER_ID = "0" * 22


def make_list_entity(kind, items):
    return {"type": kind, "name": "A List", "trackList": items}


def test_parse_embed_list_gives_the_track_links_in_order():
    items = [
        {"uri": f"spotify:track:{TRACK_ID}", "entityType": "track"},
        {"uri": f"spotify:episode:{OTHER_ID}", "entityType": "episode"},
        {"uri": "spotify:local:abc"},
        {"uri": f"spotify:track:{OTHER_ID}", "entityType": "track"},
    ]
    found = parse_embed_list(make_page(make_list_entity("playlist", items)), "playlist")
    assert found.track_links == (
        f"https://open.spotify.com/track/{TRACK_ID}",
        f"https://open.spotify.com/track/{OTHER_ID}",
    )
    assert found.name == "A List"


def test_track_list_gives_the_album_only_for_an_album():
    album = parse_embed_list(make_page(make_list_entity("album", [])), "album")
    playlist = parse_embed_list(make_page(make_list_entity("playlist", [])), "playlist")
    assert album.album == "A List"
    assert playlist.album is None


def test_parse_embed_list_refuses_the_wrong_kind():
    with pytest.raises(SpotifyError):
        parse_embed_list(make_page(make_list_entity("album", [])), "playlist")


def test_fetch_list_reads_the_embed_page_of_the_link():
    asked = []

    def get_text(url):
        asked.append(url)
        return make_page(make_list_entity("album", []))

    fetch_list(f"https://open.spotify.com/album/{TRACK_ID}", get_text)
    assert asked == [f"https://open.spotify.com/embed/album/{TRACK_ID}"]


def test_fetch_list_refuses_a_track_link():
    with pytest.raises(SpotifyError):
        fetch_list(f"https://open.spotify.com/track/{TRACK_ID}", lambda url: "")


def test_track_list_tells_when_the_list_can_be_cut():
    full = TrackList("playlist", "Mix", tuple(f"s{n}" for n in range(100)))
    short = TrackList("playlist", "Mix", tuple(f"s{n}" for n in range(99)))
    assert full.maybe_cut is True
    assert short.maybe_cut is False
