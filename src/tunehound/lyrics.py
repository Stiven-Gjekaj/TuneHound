"""Find the lyrics of a track on lrclib.net.

lrclib.net is a public lyrics database. It needs no account and no key.
TuneHound asks for lyrics only when the user gives the lyrics option.
"""

import urllib.error
import urllib.parse
from collections.abc import Callable
from typing import Any

from tunehound import http
from tunehound.track import Track

API = "https://lrclib.net/api/get"


def lyrics_url(track: Track) -> str:
    """Return the lrclib.net request for a track."""
    query = {
        "artist_name": track.artists[0],
        "track_name": track.title,
        "duration": str(round(track.duration_seconds)),
    }
    if track.album:
        query["album_name"] = track.album
    return f"{API}?{urllib.parse.urlencode(query)}"


def fetch_lyrics(
    track: Track, get_json: Callable[[str], Any] = http.get_json
) -> str | None:
    """Return the plain lyrics of a track, or None when there are none."""
    try:
        answer = get_json(lyrics_url(track))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if not isinstance(answer, dict) or answer.get("instrumental"):
        return None
    text = (answer.get("plainLyrics") or "").strip()
    return text or None
