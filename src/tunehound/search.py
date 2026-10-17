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


def search_youtube(
    track: Track,
    limit: int = SEARCH_LIMIT,
    extract: Extractor = _extract_flat,
) -> list[Candidate]:
    """Return the YouTube search results for a track."""
    info = extract(f"ytsearch{limit}:{query_for(track)}")
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
