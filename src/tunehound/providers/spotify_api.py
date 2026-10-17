"""Read Spotify tracks, albums, and playlists with the Spotify Web API.

The API needs the client ID and the client secret of a Spotify developer
app. TuneHound uses the client credentials flow, so it sees public items
only. The API gives a list in pages of up to 100 items, and TuneHound reads
every page. Since late 2024, the API refuses new apps the playlists that
Spotify itself makes.
"""

import base64
import time
import urllib.error
from collections.abc import Callable, Iterator
from typing import Any

from tunehound import http
from tunehound.providers.base import ProviderError
from tunehound.track import Track

TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"
TRACK_URL = "https://open.spotify.com/track/{id}"
PAGE_SIZE = 100
ALBUM_PAGE_SIZE = 50
# Ask for a new token a little before the old one ends.
TOKEN_MARGIN_SECONDS = 60

Request = Callable[..., Any]


class SpotifyApiError(ProviderError):
    """Tell that the Spotify Web API refused a request."""


def _release_date(album: dict) -> str | None:
    value = album.get("release_date") or ""
    return value or None


def parse_track(data: dict) -> Track:
    """Make a track from a Spotify Web API track object."""
    artists = tuple(a["name"] for a in data.get("artists") or [] if a.get("name"))
    if not data.get("name") or not artists or not data.get("id"):
        raise SpotifyApiError("the Spotify track has no ID, no title, or no artist")
    album = data.get("album") or {}
    images = album.get("images") or []
    cover = (
        max(images, key=lambda image: image.get("width") or 0)["url"]
        if images
        else None
    )
    return Track(
        title=data["name"],
        artists=artists,
        duration_ms=int(data.get("duration_ms") or 0),
        source_url=TRACK_URL.format(id=data["id"]),
        album=album.get("name") or None,
        track_number=data.get("track_number") or None,
        disc_number=data.get("disc_number") or None,
        release_date=_release_date(album),
        isrc=(data.get("external_ids") or {}).get("isrc") or None,
        cover_url=cover,
        explicit=bool(data.get("explicit", False)),
    )


class SpotifyApi:
    """Ask the Spotify Web API, with a token that it renews by itself."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        request: Request = http.request_json,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._request = request
        self._clock = clock
        self._token: str | None = None
        self._token_end = 0.0

    def _get_token(self) -> str:
        if self._token and self._clock() < self._token_end:
            return self._token
        pair = f"{self._client_id}:{self._client_secret}".encode()
        headers = {"Authorization": "Basic " + base64.b64encode(pair).decode()}
        try:
            answer = self._request(
                TOKEN_URL, headers=headers, form={"grant_type": "client_credentials"}
            )
        except urllib.error.HTTPError as error:
            if error.code in (400, 401):
                raise SpotifyApiError(
                    "Spotify refused the client ID or the client secret"
                ) from error
            raise
        self._token = answer["access_token"]
        lifetime = float(answer.get("expires_in") or 3600)
        self._token_end = self._clock() + lifetime - TOKEN_MARGIN_SECONDS
        return self._token

    def get(self, path_or_url: str) -> Any:
        """Ask for an API path, or for a full API URL from a "next" field."""
        url = path_or_url if path_or_url.startswith("http") else API + path_or_url
        headers = {"Authorization": f"Bearer {self._get_token()}"}
        try:
            return self._request(url, headers=headers)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise SpotifyApiError(
                    "Spotify did not find the item, or does not give it to this app. "
                    "Playlists that Spotify itself makes are closed to new apps."
                ) from error
            if error.code == 401:
                self._token = None
            raise SpotifyApiError(
                f"the Spotify Web API refused the request: {error}"
            ) from error

    def track(self, track_id: str) -> Track:
        """Read one track."""
        return parse_track(self.get(f"/tracks/{track_id}"))

    def _pages(self, path: str) -> Iterator[dict]:
        """Give each item of a paged list, and follow the "next" links."""
        url: str | None = path
        while url:
            page = self.get(url)
            yield from page.get("items") or []
            url = page.get("next")

    def album(self, album_id: str) -> tuple[str, list[Track]]:
        """Read the name and the tracks of an album."""
        info = self.get(f"/albums/{album_id}")
        # The tracks of an album do not hold the album, so add it.
        album = {
            "name": info.get("name"),
            "release_date": info.get("release_date"),
            "images": info.get("images") or [],
        }
        tracks = [
            parse_track({**item, "album": album})
            for item in self._pages(
                f"/albums/{album_id}/tracks?limit={ALBUM_PAGE_SIZE}"
            )
            if item and item.get("id")
        ]
        return info.get("name") or "", tracks

    def playlist(self, playlist_id: str) -> tuple[str, list[Track]]:
        """Read the name and every track of a playlist, page by page."""
        info = self.get(f"/playlists/{playlist_id}?fields=name")
        tracks = []
        for item in self._pages(f"/playlists/{playlist_id}/tracks?limit={PAGE_SIZE}"):
            data = (item or {}).get("track")
            # A playlist can hold podcast episodes, local files, and songs
            # that Spotify removed. TuneHound skips them.
            if not data or data.get("type") != "track" or data.get("is_local"):
                continue
            if not data.get("id"):
                continue
            tracks.append(parse_track(data))
        return info.get("name") or "", tracks
