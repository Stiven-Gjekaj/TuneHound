"""Fill the missing tags of a track from Deezer.

A Spotify track from the embed page has no album, no track number, and no
ISRC. Deezer has them. TuneHound looks the track up by its ISRC when it has
one, or else searches for the artist and the title and checks the result.
"""

import dataclasses
import urllib.parse
from collections.abc import Callable
from typing import Any

from tunehound import http
from tunehound.matching import normalize
from tunehound.providers import deezer
from tunehound.providers.base import ProviderError
from tunehound.track import Track

API = "https://api.deezer.com"
SEARCH_LIMIT = 5
MAX_DURATION_DIFFERENCE_MS = 5000
FILLED_FIELDS = (
    "album",
    "track_number",
    "disc_number",
    "isrc",
    "release_date",
    "cover_url",
)

GetJson = Callable[[str], Any]


def is_complete(track: Track) -> bool:
    """Tell if the track already has every field that Deezer can fill."""
    return all(getattr(track, name) for name in FILLED_FIELDS)


def _same_song(track: Track, item: dict) -> bool:
    title = normalize(item.get("title") or "")
    artist = normalize((item.get("artist") or {}).get("name") or "")
    duration_ms = int(item.get("duration") or 0) * 1000
    return (
        title == normalize(track.title)
        and artist == normalize(track.artists[0])
        and abs(duration_ms - track.duration_ms) <= MAX_DURATION_DIFFERENCE_MS
    )


def find_on_deezer(track: Track, get_json: GetJson = http.get_json) -> Track | None:
    """Return the Deezer track that is the same song, or None."""
    if track.isrc:
        answer = get_json(f"{API}/track/isrc:{urllib.parse.quote(track.isrc)}")
        if isinstance(answer, dict) and "error" not in answer and answer.get("id"):
            return deezer.parse_track(answer)
        return None
    query = urllib.parse.quote(f"{track.artists[0]} {track.title}")
    answer = get_json(f"{API}/search?q={query}&limit={SEARCH_LIMIT}")
    items = answer.get("data") if isinstance(answer, dict) else None
    for item in items or []:
        if _same_song(track, item):
            return deezer.fetch_track(deezer.TRACK_URL.format(id=item["id"]), get_json)
    return None


def enrich(track: Track, get_json: GetJson = http.get_json) -> Track:
    """Fill the empty fields of a track from Deezer, and keep the others."""
    if is_complete(track):
        return track
    try:
        found = find_on_deezer(track, get_json)
    except (OSError, ValueError, ProviderError):
        return track
    if found is None:
        return track
    changes = {
        name: getattr(found, name)
        for name in FILLED_FIELDS
        if not getattr(track, name) and getattr(found, name)
    }
    return dataclasses.replace(track, **changes) if changes else track
