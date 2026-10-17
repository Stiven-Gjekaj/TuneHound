"""Read songs from Deezer links with the public Deezer API.

The API needs no account and no key. A track gives the album, the track
number, the ISRC, the release date, and a large cover.
"""

import re
from collections.abc import Callable
from typing import Any

from tunehound import http
from tunehound.providers.base import ProviderError, TrackList
from tunehound.track import Track

API = "https://api.deezer.com"
TRACK_URL = "https://www.deezer.com/track/{id}"
PAGE_SIZE = 100

_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?deezer\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?"
    r"(?P<kind>track|album|playlist)/(?P<id>\d+)(?:[/?#].*)?$"
)
_SHORT_PATTERN = re.compile(r"^https?://(?:link\.deezer\.com|deezer\.page\.link)/\S+$")

GetJson = Callable[[str], Any]


class DeezerError(ProviderError):
    """Tell that a Deezer link or answer is not usable."""


def parse_link(link: str) -> tuple[str, str]:
    """Return the kind and the ID of a Deezer track, album, or playlist link."""
    match = _URL_PATTERN.match(link.strip())
    if not match:
        raise DeezerError(f"not a Deezer link: {link.strip()}")
    return match.group("kind"), match.group("id")


def _checked(answer: Any) -> dict:
    if not isinstance(answer, dict):
        raise DeezerError("Deezer gave an answer with an unknown shape")
    if "error" in answer:
        message = answer["error"].get("message") or "unknown error"
        raise DeezerError(f"Deezer refused the request: {message}")
    return answer


def parse_track(data: dict) -> Track:
    """Make a track from a Deezer track object."""
    names = [c.get("name") for c in data.get("contributors") or [] if c.get("name")]
    if not names and (data.get("artist") or {}).get("name"):
        names = [data["artist"]["name"]]
    if not data.get("title") or not names:
        raise DeezerError("the Deezer track has no title or no artist")
    album = data.get("album") or {}
    return Track(
        title=data["title"],
        artists=tuple(dict.fromkeys(names)),
        duration_ms=int(data.get("duration") or 0) * 1000,
        source_url=TRACK_URL.format(id=data["id"]),
        album=album.get("title") or None,
        track_number=data.get("track_position") or None,
        disc_number=data.get("disk_number") or None,
        release_date=data.get("release_date") or album.get("release_date") or None,
        isrc=data.get("isrc") or None,
        cover_url=album.get("cover_xl") or album.get("cover_big") or None,
        explicit=bool(data.get("explicit_lyrics", False)),
    )


def fetch_track(link: str, get_json: GetJson = http.get_json) -> Track:
    """Read the metadata of the track in a Deezer link."""
    kind, track_id = parse_link(link)
    if kind != "track":
        raise DeezerError(f"not a Deezer track link: {link.strip()}")
    return parse_track(_checked(get_json(f"{API}/track/{track_id}")))


def fetch_list(link: str, get_json: GetJson = http.get_json) -> TrackList:
    """Read the songs of a Deezer album or playlist link, page by page."""
    kind, list_id = parse_link(link)
    if kind not in ("album", "playlist"):
        raise DeezerError(f"not a Deezer album or playlist link: {link.strip()}")
    info = _checked(get_json(f"{API}/{kind}/{list_id}"))
    links: list[str] = []
    url: str | None = f"{API}/{kind}/{list_id}/tracks?limit={PAGE_SIZE}"
    while url:
        page = _checked(get_json(url))
        for item in page.get("data") or []:
            if item.get("id") and item.get("type", "track") == "track":
                links.append(TRACK_URL.format(id=item["id"]))
        url = page.get("next")
    return TrackList(kind=kind, name=info.get("title") or "", track_links=tuple(links))


class DeezerProvider:
    """Read songs from Deezer links."""

    name = "deezer"

    def __init__(
        self,
        get_json: GetJson = http.get_json,
        final_url: Callable[[str], str] = http.final_url,
    ) -> None:
        self._get_json = get_json
        self._final_url = final_url

    def _resolve(self, link: str) -> str:
        if _SHORT_PATTERN.match(link.strip()):
            return self._final_url(link.strip())
        return link

    def owns(self, link: str) -> bool:
        return bool(
            _URL_PATTERN.match(link.strip()) or _SHORT_PATTERN.match(link.strip())
        )

    def kind_of(self, link: str) -> str:
        return parse_link(self._resolve(link))[0]

    def fetch_track(self, link: str) -> Track:
        return fetch_track(self._resolve(link), self._get_json)

    def fetch_list(self, link: str) -> TrackList:
        return fetch_list(self._resolve(link), self._get_json)
