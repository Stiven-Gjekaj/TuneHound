"""Read songs from Spotify links.

The embed page of a track holds its metadata as JSON. The page needs no
account and no API key. It does not give the album or the ISRC.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tunehound import http
from tunehound.providers.base import ProviderError, TrackList
from tunehound.track import Track

if TYPE_CHECKING:
    from tunehound.providers.spotify_api import SpotifyApi

_ID = r"[0-9A-Za-z]{22}"
_KIND = r"(?P<kind>track|album|playlist)"
_URL_PATTERN = re.compile(
    rf"^https?://open\.spotify\.com/(?:intl-[a-z]{{2}}(?:-[a-z]{{2}})?/)?"
    rf"(?:embed/)?{_KIND}/(?P<id>{_ID})(?:[/?#].*)?$"
)
_URI_PATTERN = re.compile(rf"^spotify:{_KIND}:(?P<id>{_ID})$")
_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(?P<json>.*?)</script>',
    re.DOTALL,
)
EMBED_URL = "https://open.spotify.com/embed/{kind}/{id}"
TRACK_URL = "https://open.spotify.com/track/{id}"

# The embed page of a playlist gave 100 songs at most in a test. A list
# with this count can be cut, so TuneHound warns about it.
EMBED_LIST_LIMIT = 100


class SpotifyError(ProviderError):
    """Tell that a Spotify link or page is not usable."""


@dataclass(frozen=True)
class SpotifyLink:
    """Hold the kind and the ID of a Spotify link."""

    kind: str
    id: str


def parse_link(link: str) -> SpotifyLink:
    """Return the kind and the ID of a Spotify track, album, or playlist link."""
    link = link.strip()
    for pattern in (_URL_PATTERN, _URI_PATTERN):
        match = pattern.match(link)
        if match:
            return SpotifyLink(kind=match.group("kind"), id=match.group("id"))
    raise SpotifyError(f"not a Spotify link: {link}")


def parse_track_id(link: str) -> str:
    """Return the track ID in a Spotify link or URI."""
    parsed = parse_link(link)
    if parsed.kind != "track":
        raise SpotifyError(f"not a Spotify track link: {link.strip()}")
    return parsed.id


def _read_entity(page: str, kind: str) -> dict:
    match = _NEXT_DATA.search(page)
    if not match:
        raise SpotifyError(f"the embed page has no {kind} data")
    try:
        data = json.loads(match.group("json"))
        entity = data["props"]["pageProps"]["state"]["data"]["entity"]
    except (ValueError, KeyError, TypeError) as error:
        raise SpotifyError("the embed page has an unknown shape") from error
    if not isinstance(entity, dict) or entity.get("type") != kind:
        raise SpotifyError(f"the embed page is not for a {kind}")
    return entity


def parse_embed_page(page: str, track_id: str) -> Track:
    """Make a track from the HTML of a Spotify embed page."""
    entity = _read_entity(page, "track")

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
    page = get_text(EMBED_URL.format(kind="track", id=track_id))
    return parse_embed_page(page, track_id)


def parse_embed_list(page: str, kind: str) -> TrackList:
    """Make a track list from the HTML of an album or playlist embed page."""
    entity = _read_entity(page, kind)
    links = []
    for item in entity.get("trackList") or []:
        uri = item.get("uri") or ""
        match = _URI_PATTERN.match(uri)
        if match and match.group("kind") == "track":
            links.append(TRACK_URL.format(id=match.group("id")))
    return TrackList(
        kind=kind,
        name=entity.get("name") or "",
        track_links=tuple(links),
        cut_limit=EMBED_LIST_LIMIT if kind == "playlist" else None,
    )


def fetch_list(link: str, get_text: Callable[[str], str] = http.get_text) -> TrackList:
    """Read the songs of a Spotify album or playlist link."""
    parsed = parse_link(link)
    if parsed.kind not in ("album", "playlist"):
        raise SpotifyError(f"not a Spotify album or playlist link: {link.strip()}")
    page = get_text(EMBED_URL.format(kind=parsed.kind, id=parsed.id))
    return parse_embed_list(page, parsed.kind)


class SpotifyProvider:
    """Read songs from Spotify links.

    With an API client, the provider reads the Web API, which gives full
    lists and full tags. Without one, it reads the embed page, which needs
    no keys but gives at most 100 songs of a playlist.
    """

    name = "spotify"

    def __init__(self, api: "SpotifyApi | None" = None) -> None:
        self.api = api
        # A list from the API already holds each full track, so keep them
        # and do not ask again for each song.
        self._tracks: dict[str, Track] = {}

    def owns(self, link: str) -> bool:
        try:
            parse_link(link)
        except SpotifyError:
            return False
        return True

    def kind_of(self, link: str) -> str:
        return parse_link(link).kind

    def fetch_track(self, link: str) -> Track:
        if self.api is None:
            return fetch_track(link)
        track_id = parse_track_id(link)
        url = TRACK_URL.format(id=track_id)
        if url in self._tracks:
            return self._tracks.pop(url)
        return self.api.track(track_id)

    def fetch_list(self, link: str) -> TrackList:
        if self.api is None:
            return fetch_list(link)
        parsed = parse_link(link)
        if parsed.kind == "album":
            name, tracks = self.api.album(parsed.id)
        elif parsed.kind == "playlist":
            name, tracks = self.api.playlist(parsed.id)
        else:
            raise SpotifyError(f"not a Spotify album or playlist link: {link.strip()}")
        for track in tracks:
            self._tracks[track.source_url] = track
        return TrackList(
            kind=parsed.kind,
            name=name,
            track_links=tuple(track.source_url for track in tracks),
        )
