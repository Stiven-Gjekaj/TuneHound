"""Turn a provider link into a tagged audio file."""

import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tunehound import http
from tunehound.download import DownloadError, download_audio
from tunehound.matching import Candidate, best_match
from tunehound.providers import Provider, ProviderError, TrackList, find_provider
from tunehound.search import search_youtube
from tunehound.tagging import TaggingError, write_tags
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
    fetch: Callable[[str], Track] | None = None,
    search: Callable[[Track], list[Candidate]] = search_youtube,
    download: Callable[..., Path] = download_audio,
    get_bytes: Callable[[str], bytes] = http.get_bytes,
    tag: Callable[[Path, Track, bytes | None], None] = write_tags,
    album: str | None = None,
    track_number: int | None = None,
) -> Result:
    """Read the track of a link, find it, download it, and tag it.

    When the audio file of the track is already in the folder, do not
    search or download again.
    """
    if fetch is None:
        fetch = find_provider(link).fetch_track
    track = fetch(link)
    if album and not track.album:
        track = dataclasses.replace(track, album=album)
    if track_number and not track.track_number:
        track = dataclasses.replace(track, track_number=track_number)
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


SONG_ERRORS = (ProviderError, NoMatchError, DownloadError, TaggingError, OSError)


@dataclass(frozen=True)
class Outcome:
    """Hold what happened to one song of a link."""

    link: str
    result: Result | None = None
    error: str | None = None

    @property
    def status(self) -> str:
        """Return "downloaded", "skipped", or "failed"."""
        if self.result is None:
            return "failed"
        return "skipped" if self.result.skipped else "downloaded"


OutcomeHook = Callable[[int, int, Outcome], None]


def download_link(
    link: str,
    output_dir: Path,
    cookies_from_browser: str | None = None,
    on_outcome: OutcomeHook | None = None,
    on_list: Callable[[TrackList], None] | None = None,
    find: Callable[[str], Provider] = find_provider,
    download_song: Callable[..., Result] = download_track,
) -> list[Outcome]:
    """Download the song of a track link, or each song of a list link.

    A song that fails does not stop the other songs. `on_outcome` gets the
    number of the song, the count of songs, and the outcome, after each song.
    """
    provider = find(link)
    if provider.kind_of(link) == "track":
        songs = [(link, None, None)]
    else:
        track_list = provider.fetch_list(link)
        if on_list is not None:
            on_list(track_list)
        songs = [
            (song_link, track_list.album, number if track_list.album else None)
            for number, song_link in enumerate(track_list.track_links, start=1)
        ]

    outcomes = []
    for index, (song_link, album, number) in enumerate(songs, start=1):
        try:
            result = download_song(
                song_link,
                output_dir,
                cookies_from_browser=cookies_from_browser,
                fetch=provider.fetch_track,
                album=album,
                track_number=number,
            )
            outcome = Outcome(link=song_link, result=result)
        except SONG_ERRORS as error:
            outcome = Outcome(link=song_link, error=str(error))
        outcomes.append(outcome)
        if on_outcome is not None:
            on_outcome(index, len(songs), outcome)
    return outcomes
