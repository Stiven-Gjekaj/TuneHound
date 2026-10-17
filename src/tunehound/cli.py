"""The command line interface of TuneHound."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tunehound import __version__
from tunehound.download import CODECS, DEFAULT_CODEC


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
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.cwd(),
        help="the folder for the audio files (default: the current folder)",
    )
    options.add_argument(
        "-f",
        "--format",
        choices=CODECS,
        default=DEFAULT_CODEC,
        help="the audio format (default: mp3)",
    )
    options.add_argument(
        "--lyrics",
        action="store_true",
        help="write the lyrics from lrclib.net into the tags",
    )
    options.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="use the YouTube sign-in of a browser, for example firefox",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    download = commands.add_parser(
        "download", parents=[options], help="download the songs of a link"
    )
    download.add_argument(
        "link",
        help=(
            "a Spotify, Deezer, Apple Music, YouTube, SoundCloud, or Bandcamp "
            'link, or a search text such as "artist - title"'
        ),
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


def _print_list(track_list) -> None:
    if track_list.maybe_cut:
        print(
            f"tunehound: the list has {len(track_list.track_links)} songs. "
            "Spotify can give no more than this, so some songs can be missing.",
            file=sys.stderr,
        )


def summarize(outcomes) -> str:
    """Return one line that counts the outcomes of each kind."""
    counts = {status: 0 for status in ("downloaded", "skipped", "failed")}
    for outcome in outcomes:
        counts[outcome.status] += 1
    songs = "song" if len(outcomes) == 1 else "songs"
    parts = ", ".join(f"{count} {status}" for status, count in counts.items())
    return f"{len(outcomes)} {songs}: {parts}."


def run_download(
    link: str,
    output: Path,
    cookies_from_browser: str | None,
    codec: str = DEFAULT_CODEC,
    lyrics: bool = False,
) -> int:
    """Download the songs of a link and print what happened to each."""
    from tunehound import pipeline
    from tunehound.providers import ProviderError

    try:
        outcomes = pipeline.download_link(
            link,
            output,
            cookies_from_browser=cookies_from_browser,
            codec=codec,
            lyrics=lyrics,
            on_outcome=_print_outcome,
            on_list=_print_list,
        )
    except (ProviderError, OSError) as error:
        print(f"tunehound: {error}", file=sys.stderr)
        return 1
    print(summarize(outcomes))
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "download":
        return run_download(
            args.link,
            args.output,
            args.cookies_from_browser,
            args.format,
            args.lyrics,
        )
    parser.error(f"unknown command: {args.command}")
