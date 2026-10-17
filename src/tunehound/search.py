"""Search YouTube for the audio of a track with yt-dlp."""

from collections.abc import Callable
from typing import Any

import yt_dlp

from tunehound.matching import Candidate
from tunehound.track import Track

SEARCH_LIMIT = 10

Extractor = Callable[[str], dict[str, Any]]


def _extract_flat(url: str) -> dict[str, Any]:
    options = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(options) as downloader:
        return downloader.extract_info(url, download=False)


def query_for(track: Track) -> str:
    """Return the search text for a track."""
    return f"{track.artist} - {track.title}"


def queries_for(track: Track) -> list[str]:
    """Return the search texts for a track, best first.

    YouTube gives no results for some texts that start with an artist name
    that it reads as a typo, for example "Zericxxn - Raya". The same words
    with the title first give results, so try that order next.
    """
    queries = [query_for(track), f"{track.title} {track.artist}", track.title]
    return list(dict.fromkeys(queries))


def _candidates(info: dict[str, Any]) -> list[Candidate]:
    candidates = []
    for entry in info.get("entries") or []:
        if not entry or not entry.get("id") or not entry.get("title"):
            continue
        duration = entry.get("duration")
        candidates.append(
            Candidate(
                video_id=entry["id"],
                title=entry["title"],
                channel=entry.get("channel") or entry.get("uploader") or "",
                duration_seconds=float(duration) if duration is not None else None,
                source="youtube",
            )
        )
    return candidates


def search_youtube(
    track: Track,
    limit: int = SEARCH_LIMIT,
    extract: Extractor = _extract_flat,
) -> list[Candidate]:
    """Return the YouTube search results for a track.

    When a search text gives no results, try the next one.
    """
    for query in queries_for(track):
        candidates = _candidates(extract(f"ytsearch{limit}:{query}"))
        if candidates:
            return candidates
    return []
