"""Turn a provider link into a tagged audio file."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tunehound import http
from tunehound.download import download_audio
from tunehound.matching import Candidate, best_match
from tunehound.providers.spotify import fetch_track
from tunehound.search import search_youtube
from tunehound.tagging import write_tags
from tunehound.track import Track

MAX_FILENAME_LENGTH = 200
_UNSAFE = re.compile(r'[\x00-\x1f<>:"/\\|?*]')


class NoMatchError(Exception):
    """Tell that no search result is the same song as the track."""


@dataclass(frozen=True)
class Result:
    """Hold what one download made."""

    track: Track
    match: Candidate | None
    path: Path
    skipped: bool = False


def safe_filename(text: str) -> str:
    """Make text safe to use as a file name on Windows, macOS, and Linux."""
    name = _UNSAFE.sub("_", " ".join(text.split())).strip(" .")
    return name[:MAX_FILENAME_LENGTH].rstrip(" .") or "track"


def _fetch_cover(url: str | None, get_bytes: Callable[[str], bytes]) -> bytes | None:
    if not url:
        return None
    try:
        return get_bytes(url)
    except OSError:
        return None


def download_track(
    link: str,
    output_dir: Path,
    cookies_from_browser: str | None = None,
    fetch: Callable[[str], Track] = fetch_track,
    search: Callable[[Track], list[Candidate]] = search_youtube,
    download: Callable[..., Path] = download_audio,
    get_bytes: Callable[[str], bytes] = http.get_bytes,
    tag: Callable[[Path, Track, bytes | None], None] = write_tags,
) -> Result:
    """Read the track of a link, find it, download it, and tag it.

    When the audio file of the track is already in the folder, do not
    search or download again.
    """
    track = fetch(link)
    stem = output_dir / safe_filename(f"{track.artist} - {track.title}")
    existing = stem.with_name(f"{stem.name}.mp3")
    if existing.is_file():
        return Result(track=track, match=None, path=existing, skipped=True)
    match = best_match(track, search(track))
    if match is None:
        raise NoMatchError(f"found no result for {track.artist} - {track.title}")
    path = download(match.url, stem, cookies_from_browser=cookies_from_browser)
    tag(path, track, _fetch_cover(track.cover_url, get_bytes))
    return Result(track=track, match=match, path=path)
