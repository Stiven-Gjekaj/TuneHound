"""Find a song from a search text, for example "artist - title".

TuneHound asks the Deezer search for the text, and takes the first song.
"""

import re
import urllib.parse
from collections.abc import Callable
from typing import Any

from tunehound import http
from tunehound.providers import deezer
from tunehound.providers.base import ProviderError, TrackList
from tunehound.track import Track

SEARCH_URL = "https://api.deezer.com/search?q={query}&limit=1"
_LINK = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|spotify:)", re.IGNORECASE)


class SearchError(ProviderError):
    """Tell that a search text found no song."""


class TextSearchProvider:
    """Find the song of a search text on Deezer."""

    name = "search"

    def __init__(self, get_json: Callable[[str], Any] = http.get_json) -> None:
        self._get_json = get_json

    def owns(self, link: str) -> bool:
        text = link.strip()
        return bool(text) and not _LINK.match(text)

    def kind_of(self, link: str) -> str:
        return "track"

    def fetch_track(self, link: str) -> Track:
        query = " ".join(link.split())
        url = SEARCH_URL.format(query=urllib.parse.quote(query))
        answer = self._get_json(url)
        items = answer.get("data") if isinstance(answer, dict) else None
        if not items:
            raise SearchError(f"Deezer found no song for: {query}")
        track_link = deezer.TRACK_URL.format(id=items[0]["id"])
        return deezer.fetch_track(track_link, self._get_json)

    def fetch_list(self, link: str) -> TrackList:
        raise SearchError("a search text gives one song, not a list")
