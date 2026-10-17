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

    download = commands.add_parser("download", help="download the songs of a link")
    download.add_argument("link", help="a Spotify track, album, or playlist link")
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


def _describe(outcome) -> str:
    if outcome.result is None:
        return f"{outcome.link}: {outcome.error}"
    track = outcome.result.track
    return f"{track.artist} - {track.title}"


def _print_outcome(index: int, total: int, outcome) -> None:
    line = f"[{index}/{total}] {outcome.status:<10} {_describe(outcome)}"
    print(line, file=sys.stderr if outcome.status == "failed" else sys.stdout)


def summarize(outcomes) -> str:
    """Return one line that counts the outcomes of each kind."""
    counts = {status: 0 for status in ("downloaded", "skipped", "failed")}
    for outcome in outcomes:
        counts[outcome.status] += 1
    songs = "song" if len(outcomes) == 1 else "songs"
    parts = ", ".join(f"{count} {status}" for status, count in counts.items())
    return f"{len(outcomes)} {songs}: {parts}."


def run_download(link: str, output: Path, cookies_from_browser: str | None) -> int:
    """Download the songs of a link and print what happened to each."""
    from tunehound import pipeline
    from tunehound.providers.spotify import SpotifyError

    try:
        outcomes = pipeline.download_link(
            link,
            output,
            cookies_from_browser=cookies_from_browser,
            on_outcome=_print_outcome,
        )
    except (SpotifyError, OSError) as error:
        print(f"tunehound: {error}", file=sys.stderr)
        return 1
    print(summarize(outcomes))
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0


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
