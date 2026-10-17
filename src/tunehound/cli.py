"""The command line interface of TuneHound."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tunehound import __version__


def build_parser() -> argparse.ArgumentParser:
    """Make the parser for the command line."""
    parser = argparse.ArgumentParser(
        prog="tunehound",
        description="Download music from many providers with yt-dlp.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    commands.add_parser("tui", help="open the terminal user interface")

    download = commands.add_parser("download", help="download a song from a link")
    download.add_argument("link", help="a Spotify track link")
    download.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.cwd(),
        help="the folder for the audio file (default: the current folder)",
    )
    download.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="use the YouTube sign-in of a browser, for example firefox",
    )
    return parser


def run_download(link: str, output: Path, cookies_from_browser: str | None) -> int:
    """Download one song and print where it is."""
    from tunehound.download import DownloadError
    from tunehound.pipeline import NoMatchError, download_track
    from tunehound.providers.spotify import SpotifyError
    from tunehound.tagging import TaggingError

    try:
        result = download_track(link, output, cookies_from_browser=cookies_from_browser)
    except (SpotifyError, NoMatchError, DownloadError, TaggingError, OSError) as error:
        print(f"tunehound: {error}", file=sys.stderr)
        return 1
    print(f"{result.track.artist} - {result.track.title}")
    print(f"  from {result.match.url}")
    print(f"  to   {result.path}")
    return 0


def run_tui() -> int:
    """Open the terminal user interface."""
    from tunehound.tui import TuneHoundApp

    TuneHoundApp().run()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "tui":
        return run_tui()
    if args.command == "download":
        return run_download(args.link, args.output, args.cookies_from_browser)
    parser.error(f"unknown command: {args.command}")
