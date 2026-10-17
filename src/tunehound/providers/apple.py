"""Read songs from Apple Music links with the public iTunes lookup API.

The API needs no account and no key. It gives songs and albums. It does not
give playlists.
"""

import re
from collections.abc import Callable
from typing import Any

from tunehound import http
from tunehound.providers.base import ProviderError, TrackList
from tunehound.track import Track

LOOKUP = "https://itunes.apple.com/lookup?id={id}&country={country}"
SONG_URL = "https://music.apple.com/{country}/song/{id}"
COVER_SIZE = "1000x1000bb"

_HOST = r"^https?://(?:geo\.)?music\.apple\.com/(?P<country>[a-z]{2})/"
_SONG_PATTERN = re.compile(_HOST + r"song/(?:[^/?#]+/)?(?P<id>\d+)(?:[/?#].*)?$")
_ALBUM_PATTERN = re.compile(
    _HOST + r"album/(?:[^/?#]+/)?(?P<id>\d+)/?(?:\?(?P<query>[^#]*))?(?:#.*)?$"
)
_TRACK_IN_QUERY = re.compile(r"(?:^|&)i=(?P<id>\d+)(?:&|$)")

GetJson = Callable[[str], Any]


class AppleMusicError(ProviderError):
    """Tell that an Apple Music link or answer is not usable."""


def parse_link(link: str) -> tuple[str, str, str]:
    """Return the kind, the ID, and the country of an Apple Music link."""
    link = link.strip()
    match = _SONG_PATTERN.match(link)
    if match:
        return "track", match.group("id"), match.group("country")
    match = _ALBUM_PATTERN.match(link)
    if match:
        track = _TRACK_IN_QUERY.search(match.group("query") or "")
        if track:
            return "track", track.group("id"), match.group("country")
        return "album", match.group("id"), match.group("country")
    raise AppleMusicError(f"not an Apple Music song or album link: {link}")


def _results(answer: Any) -> list[dict]:
    if not isinstance(answer, dict) or not isinstance(answer.get("results"), list):
        raise AppleMusicError("Apple gave an answer with an unknown shape")
    return answer["results"]


def parse_song(data: dict, country: str) -> Track:
    """Make a track from an iTunes song object."""
    if data.get("kind") != "song" or not data.get("trackName"):
        raise AppleMusicError("the Apple Music item is not a song")
    if not data.get("artistName"):
        raise AppleMusicError("the Apple Music song has no artist")
    artwork = data.get("artworkUrl100") or ""
    cover_url = re.sub(r"\d+x\d+bb", COVER_SIZE, artwork) if artwork else None
    return Track(
        title=data["trackName"],
        artists=(data["artistName"],),
        duration_ms=int(data.get("trackTimeMillis") or 0),
        source_url=SONG_URL.format(country=country, id=data["trackId"]),
        album=data.get("collectionName") or None,
        track_number=data.get("trackNumber") or None,
        disc_number=data.get("discNumber") or None,
        release_date=(data.get("releaseDate") or "")[:10] or None,
        cover_url=cover_url,
        explicit=data.get("trackExplicitness") == "explicit",
    )


def fetch_track(link: str, get_json: GetJson = http.get_json) -> Track:
    """Read the metadata of the song in an Apple Music link."""
    kind, song_id, country = parse_link(link)
    if kind != "track":
        raise AppleMusicError(f"not an Apple Music song link: {link.strip()}")
    results = _results(get_json(LOOKUP.format(id=song_id, country=country)))
    if not results:
        raise AppleMusicError(f"Apple Music has no song with the ID {song_id}")
    return parse_song(results[0], country)


def fetch_list(link: str, get_json: GetJson = http.get_json) -> TrackList:
    """Read the songs of an Apple Music album link, in the order of the discs."""
    kind, album_id, country = parse_link(link)
    if kind != "album":
        raise AppleMusicError(f"not an Apple Music album link: {link.strip()}")
    url = LOOKUP.format(id=album_id, country=country) + "&entity=song"
    results = _results(get_json(url))
    albums = [item for item in results if item.get("wrapperType") == "collection"]
    if not albums:
        raise AppleMusicError(f"Apple Music has no album with the ID {album_id}")
    songs = sorted(
        (item for item in results if item.get("kind") == "song"),
        key=lambda item: (item.get("discNumber") or 0, item.get("trackNumber") or 0),
    )
    return TrackList(
        kind="album",
        name=albums[0].get("collectionName") or "",
        track_links=tuple(
            SONG_URL.format(country=country, id=item["trackId"]) for item in songs
        ),
    )


class AppleMusicProvider:
    """Read songs from Apple Music links."""

    name = "apple"

    def __init__(self, get_json: GetJson = http.get_json) -> None:
        self._get_json = get_json

    def owns(self, link: str) -> bool:
        try:
            parse_link(link)
        except AppleMusicError:
            return False
        return True

    def kind_of(self, link: str) -> str:
        return parse_link(link)[0]

    def fetch_track(self, link: str) -> Track:
        return fetch_track(link, self._get_json)

    def fetch_list(self, link: str) -> TrackList:
        return fetch_list(link, self._get_json)
