"""Turn a provider link into a tagged audio file."""

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tunehound import http
from tunehound.download import DEFAULT_CODEC, DownloadError, download_audio
from tunehound.enrich import enrich
from tunehound.lyrics import fetch_lyrics
from tunehound.matching import Candidate, best_match
from tunehound.naming import DEFAULT_TEMPLATE, render
from tunehound.providers import Provider, ProviderError, TrackList, find_provider
from tunehound.search import search_youtube
from tunehound.tagging import TaggingError, image_mime, write_tags
from tunehound.track import Track


class NoMatchError(Exception):
    """Tell that no search result is the same song as the track."""


@dataclass(frozen=True)
class Result:
    """Hold what one download made."""

    track: Track
    match: Candidate | None
    path: Path
    skipped: bool = False


def _fetch_cover(url: str | None, get_bytes: Callable[[str], bytes]) -> bytes | None:
    if not url:
        return None
    try:
        data = get_bytes(url)
        image_mime(data)
    except (OSError, TaggingError):
        return None
    return data


def _progress_hook(
    progress: Callable[[float], None] | None,
) -> Callable[[dict], None] | None:
    """Turn the status of yt-dlp into a fraction from 0 to 1."""
    if progress is None:
        return None

    def hook(status: dict) -> None:
        if status.get("status") == "finished":
            progress(1.0)
            return
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        done = status.get("downloaded_bytes")
        if total and done is not None:
            progress(min(done / total, 1.0))

    return hook


def _find_lyrics(
    track: Track, find_lyrics: Callable[[Track], str | None]
) -> str | None:
    try:
        return find_lyrics(track)
    except (OSError, ValueError):
        return None


def download_track(
    link: str,
    output_dir: Path,
    cookies_from_browser: str | None = None,
    fetch: Callable[[str], Track] | None = None,
    search: Callable[[Track], list[Candidate]] = search_youtube,
    download: Callable[..., Path] = download_audio,
    get_bytes: Callable[[str], bytes] = http.get_bytes,
    tag: Callable[..., None] = write_tags,
    album: str | None = None,
    track_number: int | None = None,
    direct: bool = False,
    codec: str = DEFAULT_CODEC,
    fill: Callable[[Track], Track] = enrich,
    lyrics: bool = False,
    find_lyrics: Callable[[Track], str | None] = fetch_lyrics,
    progress: Callable[[float], None] | None = None,
    template: str = DEFAULT_TEMPLATE,
) -> Result:
    """Read the track of a link, find it, download it, and tag it.

    When the audio file of the track is already in the folder, do not
    search or download again. When `direct` is true, the link already points
    at the audio, so download its source with no search.
    """
    if fetch is None:
        fetch = find_provider(link).fetch_track
    track = fetch(link)
    if album and not track.album:
        track = dataclasses.replace(track, album=album)
    if track_number and not track.track_number:
        track = dataclasses.replace(track, track_number=track_number)
    if not direct:
        track = fill(track)
    stem = output_dir / render(template, track)
    existing = stem.with_name(f"{stem.name}.{codec}")
    if existing.is_file():
        return Result(track=track, match=None, path=existing, skipped=True)
    if direct:
        match = None
        url = track.source_url
    else:
        match = best_match(track, search(track))
        if match is None:
            raise NoMatchError(f"found no result for {track.artist} - {track.title}")
        url = match.url
    path = download(
        url,
        stem,
        codec=codec,
        cookies_from_browser=cookies_from_browser,
        progress_hook=_progress_hook(progress),
    )
    text = _find_lyrics(track, find_lyrics) if lyrics else None
    tag(path, track, _fetch_cover(track.cover_url, get_bytes), text)
    return Result(track=track, match=match, path=path)


def _bind_progress(
    on_progress: Callable[[int, float], None], index: int
) -> Callable[[float], None]:
    return lambda fraction: on_progress(index, fraction)


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
StartHook = Callable[[int, int, str], None]
ProgressHook = Callable[[int, float], None]


def download_link(
    link: str,
    output_dir: Path,
    cookies_from_browser: str | None = None,
    codec: str = DEFAULT_CODEC,
    lyrics: bool = False,
    template: str = DEFAULT_TEMPLATE,
    on_outcome: OutcomeHook | None = None,
    on_list: Callable[[TrackList], None] | None = None,
    on_start: StartHook | None = None,
    on_progress: ProgressHook | None = None,
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
        if on_start is not None:
            on_start(index, len(songs), song_link)
        progress = None
        if on_progress is not None:
            progress = _bind_progress(on_progress, index)
        try:
            result = download_song(
                song_link,
                output_dir,
                cookies_from_browser=cookies_from_browser,
                fetch=provider.fetch_track,
                direct=getattr(provider, "direct", False),
                codec=codec,
                lyrics=lyrics,
                progress=progress,
                template=template,
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
