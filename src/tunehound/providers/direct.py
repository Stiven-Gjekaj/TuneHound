"""Read songs from links that yt-dlp can download with no match step.

These are YouTube, YouTube Music, SoundCloud, and Bandcamp links. The link
already points at the audio, so TuneHound downloads it as it is.
"""

import re
import urllib.parse
from collections.abc import Callable
from typing import Any

import yt_dlp

from tunehound.download import short_message
from tunehound.matching import normalize
from tunehound.providers.base import ProviderError, TrackList
from tunehound.track import Track

Extractor = Callable[[str, bool], dict[str, Any]]

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
_SOUNDCLOUD_HOSTS = {"soundcloud.com", "www.soundcloud.com", "m.soundcloud.com"}
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


class DirectError(ProviderError):
    """Tell that yt-dlp cannot read a link."""


def _extract(link: str, flat: bool) -> dict[str, Any]:
    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    if flat:
        options["extract_flat"] = True
    else:
        options["noplaylist"] = True
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            return downloader.extract_info(link, download=False)
    except yt_dlp.utils.DownloadError as error:
        raise DirectError(short_message(str(error))) from error


def _host(link: str) -> str:
    return (urllib.parse.urlsplit(link.strip()).hostname or "").lower()


def link_kind(link: str) -> str | None:
    """Return the kind of a direct link, or None when it is not one."""
    parts = urllib.parse.urlsplit(link.strip())
    host = (parts.hostname or "").lower()
    query = urllib.parse.parse_qs(parts.query)
    if host in _YOUTUBE_HOSTS:
        if parts.path.startswith("/playlist") or ("list" in query and "v" not in query):
            return "playlist"
        if parts.path.startswith(("/watch", "/shorts/", "/live/")):
            return "track"
        return None
    if host == "youtu.be":
        return "track" if parts.path.strip("/") else None
    if host in _SOUNDCLOUD_HOSTS:
        if "/sets/" in parts.path:
            return "playlist"
        return "track" if parts.path.count("/") >= 2 else None
    if host == "api.soundcloud.com" and parts.path.startswith("/tracks/"):
        return "track"
    if host.endswith(".bandcamp.com"):
        if parts.path.startswith("/album/"):
            return "album"
        if parts.path.startswith("/track/"):
            return "track"
    return None


def _date(value: str | None) -> str | None:
    if value and re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return None


def _cover(info: dict[str, Any]) -> str | None:
    def is_image(url: str) -> bool:
        return urllib.parse.urlsplit(url).path.lower().endswith(_IMAGE_SUFFIXES)

    thumbnails = [t for t in info.get("thumbnails") or [] if is_image(t.get("url", ""))]
    if thumbnails:
        best = max(
            thumbnails,
            key=lambda t: (
                (t.get("width") or 0) * (t.get("height") or 0),
                t.get("preference") or 0,
            ),
        )
        return best["url"]
    thumbnail = info.get("thumbnail") or ""
    return thumbnail if is_image(thumbnail) else None


def parse_info(info: dict[str, Any], link: str) -> Track:
    """Make a track from the metadata that yt-dlp gives for one item."""
    artists = info.get("artists") or []
    if not artists:
        for key in ("artist", "creator", "uploader", "channel"):
            if info.get(key):
                artists = [info[key]]
                break
    if not artists:
        artists = ["Unknown Artist"]
    title = info.get("track") or info.get("title") or "Unknown Title"
    prefix = f"{normalize(artists[0])} "
    if " - " in title and normalize(title.split(" - ", 1)[0]) + " " == prefix:
        title = title.split(" - ", 1)[1]
    duration = info.get("duration") or 0
    return Track(
        title=title,
        artists=tuple(artists),
        duration_ms=round(float(duration) * 1000),
        source_url=info.get("webpage_url") or link.strip(),
        album=info.get("album") or None,
        track_number=info.get("track_number") or None,
        release_date=_date(info.get("release_date")) or _date(info.get("upload_date")),
        cover_url=_cover(info),
    )


class DirectProvider:
    """Read songs from links that yt-dlp downloads with no match step."""

    name = "direct"
    direct = True

    def __init__(self, extract: Extractor = _extract) -> None:
        self._extract = extract

    def owns(self, link: str) -> bool:
        return link_kind(link) is not None

    def kind_of(self, link: str) -> str:
        kind = link_kind(link)
        if kind is None:
            raise DirectError(
                f"not a YouTube, SoundCloud, or Bandcamp link: {link.strip()}"
            )
        return kind

    def fetch_track(self, link: str) -> Track:
        return parse_info(self._extract(link, False), link)

    def fetch_list(self, link: str) -> TrackList:
        kind = self.kind_of(link)
        info = self._extract(link, True)
        links = []
        for entry in info.get("entries") or []:
            if not entry:
                continue
            url = entry.get("url") or entry.get("webpage_url")
            if not url:
                continue
            if not url.startswith("http") and entry.get("ie_key") == "Youtube":
                url = f"https://www.youtube.com/watch?v={url}"
            links.append(url)
        return TrackList(
            kind=kind, name=info.get("title") or "", track_links=tuple(links)
        )
