"""Read songs from Spotify links.

The embed page of a track holds its metadata as JSON. The page needs no
account and no API key. It does not give the album or the ISRC.
"""

import json
import re
from collections.abc import Callable

from tunehound import http
from tunehound.track import Track

_ID = r"[0-9A-Za-z]{22}"
_URL_PATTERN = re.compile(
    rf"^https?://open\.spotify\.com/(?:intl-[a-z]{{2}}(?:-[a-z]{{2}})?/)?"
    rf"(?:embed/)?track/(?P<id>{_ID})(?:[/?#].*)?$"
)
_URI_PATTERN = re.compile(rf"^spotify:track:(?P<id>{_ID})$")
_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(?P<json>.*?)</script>',
    re.DOTALL,
)
EMBED_URL = "https://open.spotify.com/embed/track/{id}"
TRACK_URL = "https://open.spotify.com/track/{id}"


class SpotifyError(Exception):
    """Tell that a Spotify link or page is not usable."""


def parse_track_id(link: str) -> str:
    """Return the track ID in a Spotify link or URI."""
    link = link.strip()
    for pattern in (_URL_PATTERN, _URI_PATTERN):
        match = pattern.match(link)
        if match:
            return match.group("id")
    raise SpotifyError(f"not a Spotify track link: {link}")


def parse_embed_page(page: str, track_id: str) -> Track:
    """Make a track from the HTML of a Spotify embed page."""
    match = _NEXT_DATA.search(page)
    if not match:
        raise SpotifyError("the embed page has no track data")
    try:
        data = json.loads(match.group("json"))
        entity = data["props"]["pageProps"]["state"]["data"]["entity"]
    except (ValueError, KeyError, TypeError) as error:
        raise SpotifyError("the embed page has an unknown shape") from error
    if entity.get("type") != "track":
        raise SpotifyError("the embed page is not for a track")

    artists = tuple(artist["name"] for artist in entity.get("artists", []))
    if not entity.get("name") or not artists:
        raise SpotifyError("the embed page has no title or no artist")

    release = entity.get("releaseDate") or {}
    release_date = (release.get("isoString") or "")[:10] or None

    images = (entity.get("visualIdentity") or {}).get("image") or []
    cover_url = None
    if images:
        cover_url = max(images, key=lambda image: image.get("maxWidth", 0))["url"]

    return Track(
        title=entity["name"],
        artists=artists,
        duration_ms=int(entity.get("duration", 0)),
        source_url=TRACK_URL.format(id=track_id),
        release_date=release_date,
        cover_url=cover_url,
        explicit=bool(entity.get("isExplicit", False)),
    )


def fetch_track(link: str, get_text: Callable[[str], str] = http.get_text) -> Track:
    """Read the metadata of the track in a Spotify link."""
    track_id = parse_track_id(link)
    page = get_text(EMBED_URL.format(id=track_id))
    return parse_embed_page(page, track_id)
