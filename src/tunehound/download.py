"""Download the audio of a search result with yt-dlp."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp

DEFAULT_CODEC = "mp3"

ProgressHook = Callable[[dict[str, Any]], None]


class DownloadError(Exception):
    """Tell that yt-dlp did not make the audio file."""


def build_options(
    stem: Path,
    codec: str = DEFAULT_CODEC,
    progress_hook: ProgressHook | None = None,
) -> dict[str, Any]:
    """Make the yt-dlp options that write the audio to `stem` plus the codec."""
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": f"{stem}.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "0",
            }
        ],
    }
    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]
    return options


def download_audio(
    url: str,
    stem: Path,
    codec: str = DEFAULT_CODEC,
    progress_hook: ProgressHook | None = None,
    downloader_factory: Callable[[dict[str, Any]], Any] = yt_dlp.YoutubeDL,
) -> Path:
    """Download the audio at a URL and return the path of the audio file."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    options = build_options(stem, codec, progress_hook)
    try:
        with downloader_factory(options) as downloader:
            downloader.download([url])
    except yt_dlp.utils.DownloadError as error:
        raise DownloadError(str(error)) from error
    path = stem.with_name(f"{stem.name}.{codec}")
    if not path.is_file():
        raise DownloadError(f"yt-dlp did not make {path}")
    return path
