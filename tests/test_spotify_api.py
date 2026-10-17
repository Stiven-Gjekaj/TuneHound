import io
import urllib.error

import pytest

from tunehound.providers.spotify_api import SpotifyApi, SpotifyApiError, parse_track

TRACK_ID = "4uLU6hMCjMI75M1A2tKUQC"


def make_track(**changes):
    data = {
        "id": TRACK_ID,
        "type": "track",
        "name": "A Song",
        "duration_ms": 213573,
        "track_number": 3,
        "disc_number": 1,
        "explicit": True,
        "external_ids": {"isrc": "GBXXX0000001"},
        "artists": [{"name": "Main"}, {"name": "Guest"}],
        "album": {
            "name": "An Album",
            "release_date": "1987-11-12",
            "images": [
                {"url": "https://img.invalid/300", "width": 300},
                {"url": "https://img.invalid/640", "width": 640},
            ],
        },
    }
    data.update(changes)
    return data


class FakeSpotify:
    """Answer like the token endpoint and the API, and record each request."""

    def __init__(self, answers=None, token_lifetime=3600):
        self.answers = answers or {}
        self.token_lifetime = token_lifetime
        self.requests = []
        self.tokens = 0

    def __call__(self, url, headers=None, form=None):
        self.requests.append((url, headers, form))
        if form is not None:
            self.tokens += 1
            return {
                "access_token": f"token{self.tokens}",
                "expires_in": self.token_lifetime,
            }
        answer = self.answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer


def http_error(code):
    return urllib.error.HTTPError("https://x.invalid", code, "x", {}, io.BytesIO())


def test_parse_track_reads_all_fields():
    track = parse_track(make_track())
    assert track.title == "A Song"
    assert track.artists == ("Main", "Guest")
    assert track.duration_ms == 213573
    assert track.album == "An Album"
    assert (track.track_number, track.disc_number) == (3, 1)
    assert track.release_date == "1987-11-12"
    assert track.isrc == "GBXXX0000001"
    assert track.cover_url == "https://img.invalid/640"
    assert track.explicit is True
    assert track.source_url == f"https://open.spotify.com/track/{TRACK_ID}"


def test_parse_track_accepts_a_track_with_few_fields():
    track = parse_track({"id": "x", "name": "T", "artists": [{"name": "A"}]})
    assert (track.album, track.isrc, track.cover_url, track.release_date) == (
        None,
        None,
        None,
        None,
    )


def test_parse_track_refuses_a_track_with_no_artist():
    with pytest.raises(SpotifyApiError):
        parse_track(make_track(artists=[]))


def test_track_gets_a_token_and_asks_the_api():
    fake = FakeSpotify({f"https://api.spotify.com/v1/tracks/{TRACK_ID}": make_track()})
    api = SpotifyApi("id", "secret", request=fake)
    assert api.track(TRACK_ID).title == "A Song"
    token_url, token_headers, form = fake.requests[0]
    assert token_url == "https://accounts.spotify.com/api/token"
    assert token_headers == {"Authorization": "Basic aWQ6c2VjcmV0"}
    assert form == {"grant_type": "client_credentials"}
    assert fake.requests[1][1] == {"Authorization": "Bearer token1"}


def test_the_token_is_kept_until_it_ends():
    now = [0.0]
    url = f"https://api.spotify.com/v1/tracks/{TRACK_ID}"
    fake = FakeSpotify({url: make_track()}, token_lifetime=120)
    api = SpotifyApi("id", "secret", request=fake, clock=lambda: now[0])
    api.track(TRACK_ID)
    now[0] = 59.0
    api.track(TRACK_ID)
    assert fake.tokens == 1
    now[0] = 61.0
    api.track(TRACK_ID)
    assert fake.tokens == 2


def test_bad_keys_give_a_clear_error():
    def refuse(url, headers=None, form=None):
        raise http_error(400)

    with pytest.raises(SpotifyApiError, match="client ID or the client secret"):
        SpotifyApi("id", "bad", request=refuse).track(TRACK_ID)


def test_a_missing_item_gives_a_clear_error():
    url = f"https://api.spotify.com/v1/tracks/{TRACK_ID}"
    api = SpotifyApi("id", "secret", request=FakeSpotify({url: http_error(404)}))
    with pytest.raises(SpotifyApiError, match="did not find the item"):
        api.track(TRACK_ID)


def test_a_refused_token_is_asked_again_next_time():
    url = f"https://api.spotify.com/v1/tracks/{TRACK_ID}"
    fake = FakeSpotify({url: http_error(401)})
    api = SpotifyApi("id", "secret", request=fake)
    with pytest.raises(SpotifyApiError):
        api.track(TRACK_ID)
    fake.answers[url] = make_track()
    api.track(TRACK_ID)
    assert fake.tokens == 2


API = "https://api.spotify.com/v1"


def test_playlist_reads_every_page_and_skips_what_is_not_a_song():
    first = f"{API}/playlists/P/tracks?limit=100"
    second = f"{API}/playlists/P/tracks?offset=100&limit=100"
    fake = FakeSpotify(
        {
            f"{API}/playlists/P?fields=name": {"name": "Mix"},
            first: {
                "items": [
                    {"track": make_track(id="a")},
                    {"track": None},
                    {"track": make_track(id="b", type="episode")},
                    {"track": make_track(id="c", is_local=True)},
                ],
                "next": second,
            },
            second: {"items": [{"track": make_track(id="d")}, {}], "next": None},
        }
    )
    name, tracks = SpotifyApi("id", "secret", request=fake).playlist("P")
    assert name == "Mix"
    assert [t.source_url.rsplit("/", 1)[1] for t in tracks] == ["a", "d"]
    assert tracks[0].isrc == "GBXXX0000001"
    assert fake.tokens == 1


def test_album_adds_the_album_to_each_track():
    tracks_url = f"{API}/albums/A/tracks?limit=50"
    fake = FakeSpotify(
        {
            f"{API}/albums/A": {
                "name": "An Album",
                "release_date": "1987",
                "images": [{"url": "https://img.invalid/640", "width": 640}],
            },
            tracks_url: {
                "items": [
                    {
                        "id": "1",
                        "name": "One",
                        "artists": [{"name": "Main"}],
                        "track_number": 1,
                    },
                    {
                        "id": "2",
                        "name": "Two",
                        "artists": [{"name": "Main"}],
                        "track_number": 2,
                    },
                ],
                "next": None,
            },
        }
    )
    name, tracks = SpotifyApi("id", "secret", request=fake).album("A")
    assert name == "An Album"
    assert [(t.title, t.track_number, t.album) for t in tracks] == [
        ("One", 1, "An Album"),
        ("Two", 2, "An Album"),
    ]
    assert tracks[0].release_date == "1987"
    assert tracks[0].cover_url == "https://img.invalid/640"
