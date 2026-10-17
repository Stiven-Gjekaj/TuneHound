import pytest

from tunehound.providers.spotify import SpotifyError, parse_track_id

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
