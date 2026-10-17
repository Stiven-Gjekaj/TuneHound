"""Download the audio of a search result with yt-dlp."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp

DEFAULT_CODEC = "mp3"

ProgressHook = Callable[[dict[str, Any]], None]


class DownloadError(Exception):
    """Tell that yt-dlp did not make the audio file."""


BOT_CHECK_HINT = (
    "YouTube asks for a sign-in to confirm that this is not a bot. "
    "Use --cookies-from-browser BROWSER."
)


class _SilentLogger:
    """Keep yt-dlp from printing. TuneHound reports the errors itself."""

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def short_message(text: str) -> str:
    """Make a yt-dlp error message short enough for one line."""
    if "Sign in to confirm" in text:
        return BOT_CHECK_HINT
    text = text.removeprefix("ERROR: ")
    if text.startswith("[") and "]: " in text:
        text = text.split("]: ", 1)[1]
    elif text.startswith("[") and ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(". ", 1)[0].strip()


def build_options(
    stem: Path,
    codec: str = DEFAULT_CODEC,
    progress_hook: ProgressHook | None = None,
    cookies_from_browser: str | None = None,
) -> dict[str, Any]:
    """Make the yt-dlp options that write the audio to `stem` plus the codec.

    `cookies_from_browser` names a browser, for example "firefox". yt-dlp
    then reads the YouTube sign-in of that browser. YouTube asks for a
    sign-in when it thinks that the request comes from a bot.
    """
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": f"{stem}.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _SilentLogger(),
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
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    return options


def download_audio(
    url: str,
    stem: Path,
    codec: str = DEFAULT_CODEC,
    progress_hook: ProgressHook | None = None,
    cookies_from_browser: str | None = None,
    downloader_factory: Callable[[dict[str, Any]], Any] = yt_dlp.YoutubeDL,
) -> Path:
    """Download the audio at a URL and return the path of the audio file."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    options = build_options(stem, codec, progress_hook, cookies_from_browser)
    try:
        with downloader_factory(options) as downloader:
            downloader.download([url])
    except yt_dlp.utils.DownloadError as error:
        raise DownloadError(short_message(str(error))) from error
    path = stem.with_name(f"{stem.name}.{codec}")
    if not path.is_file():
        raise DownloadError(f"yt-dlp did not make {path}")
    return path
