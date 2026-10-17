"""The command line interface of TuneHound."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tunehound import __version__
from tunehound.config import ConfigError, default_path, load, shown, spotify_keys
from tunehound.download import CODECS, DEFAULT_CODEC
from tunehound.naming import DEFAULT_TEMPLATE, FIELDS, TemplateError, check_template


def template_argument(text: str) -> str:
    """Check a file name template on the command line."""
    try:
        check_template(text)
    except TemplateError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return text


def _add_config_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        metavar="FILE",
        help=f"the configuration file (default: {default_path()})",
    )


def build_parser(defaults: dict | None = None) -> argparse.ArgumentParser:
    """Make the parser for the command line.

    `defaults` holds the values of the configuration file. A value on the
    command line wins over them.
    """
    defaults = defaults or {}
    parser = argparse.ArgumentParser(
        prog="tunehound",
        description="Download music from many providers with yt-dlp.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    _add_config_option(parser)
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "-o",
        "--output",
        type=Path,
        default=defaults.get("output", Path.cwd()),
        help="the folder for the audio files (default: the current folder)",
    )
    options.add_argument(
        "-f",
        "--format",
        choices=CODECS,
        default=defaults.get("format", DEFAULT_CODEC),
        help="the audio format (default: mp3)",
    )
    options.add_argument(
        "--lyrics",
        action=argparse.BooleanOptionalAction,
        default=defaults.get("lyrics", False),
        help="write the lyrics from lrclib.net into the tags",
    )
    options.add_argument(
        "-t",
        "--template",
        type=template_argument,
        default=defaults.get("template", DEFAULT_TEMPLATE),
        help=(
            f'the path of each file, with no suffix (default: "{DEFAULT_TEMPLATE}"). '
            "A slash makes a folder. Fields: "
            + ", ".join(f"{{{name}}}" for name in FIELDS)
        ),
    )
    options.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        default=defaults.get("cookies_from_browser"),
        help="use the YouTube sign-in of a browser, for example firefox",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    commands.add_parser(
        "config", help="show the path and the values of the configuration file"
    )
    download = commands.add_parser(
        "download", parents=[options], help="download the songs of a link"
    )
    download.add_argument(
        "link",
        nargs="?",
        help=(
            "a Spotify, Deezer, Apple Music, YouTube, SoundCloud, or Bandcamp "
            'link, or a search text such as "artist - title"'
        ),
    )
    download.add_argument(
        "-i",
        "--input",
        type=Path,
        metavar="FILE",
        help=(
            "a text file with one link or search text on each line, in place "
            "of LINK. Empty lines and lines that start with # do not count."
        ),
    )
    return parser


def read_input(path: Path) -> list[str]:
    """Return the links and search texts of an input file, one for each line."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def _describe(outcome) -> str:
    if outcome.result is None:
        return f"{outcome.link}: {outcome.error}"
    track = outcome.result.track
    return f"{track.artist} - {track.title}"


def _print_outcome(index: int, total: int, outcome) -> None:
    line = f"[{index}/{total}] {outcome.status:<10} {_describe(outcome)}"
    print(
        line,
        file=sys.stderr if outcome.status == "failed" else sys.stdout,
        flush=True,
    )


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
    template: str = DEFAULT_TEMPLATE,
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
            template=template,
            on_outcome=_print_outcome,
            on_list=_print_list,
        )
    except (ProviderError, OSError) as error:
        print(f"tunehound: {error}", file=sys.stderr)
        return 1
    print(summarize(outcomes))
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0


def _line_printer(line: int, lines: int):
    def print_outcome(index: int, total: int, outcome) -> None:
        position = f"{line}/{lines}"
        if total > 1:
            position += f" song {index}/{total}"
        text = f"[{position}] {outcome.status:<10} {_describe(outcome)}"
        print(
            text,
            file=sys.stderr if outcome.status == "failed" else sys.stdout,
            flush=True,
        )

    return print_outcome


def run_download_many(
    links: list[str],
    output: Path,
    cookies_from_browser: str | None,
    codec: str = DEFAULT_CODEC,
    lyrics: bool = False,
    template: str = DEFAULT_TEMPLATE,
) -> int:
    """Download the songs of many links, one link after the other.

    A link that fails does not stop the other links.
    """
    from tunehound import pipeline
    from tunehound.providers import ProviderError

    outcomes = []
    for line, link in enumerate(links, start=1):
        print_outcome = _line_printer(line, len(links))
        try:
            outcomes += pipeline.download_link(
                link,
                output,
                cookies_from_browser=cookies_from_browser,
                codec=codec,
                lyrics=lyrics,
                template=template,
                on_outcome=print_outcome,
                on_list=_print_list,
            )
        except (ProviderError, OSError) as error:
            failed = pipeline.Outcome(link=link, error=str(error))
            print_outcome(1, 1, failed)
            outcomes.append(failed)
    print(summarize(outcomes))
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0


def run_config(path: Path, values: dict) -> int:
    """Print the path of the configuration file and the values in it."""
    state = "found" if path.is_file() else "not found, so TuneHound uses the defaults"
    print(f"{path} ({state})")
    for key, value in values.items():
        print(f"  {key} = {shown(key, value)}")
    keys = spotify_keys(values)
    if keys is None:
        print("Spotify: the embed page, with at most 100 songs of a playlist")
    else:
        print("Spotify: the Web API, with the full lists")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code."""
    # Read the configuration file first, because its values are the
    # defaults of the real parser.
    first = argparse.ArgumentParser(add_help=False)
    _add_config_option(first)
    known, _ = first.parse_known_args(argv)
    path = known.config or default_path()
    try:
        values = load(path)
        keys = spotify_keys(values)
    except ConfigError as error:
        print(f"tunehound: {error}", file=sys.stderr)
        return 2
    if keys is not None:
        from tunehound.providers import use_spotify_api

        use_spotify_api(*keys)
    if known.config is not None and not path.is_file():
        print(
            f"tunehound: the configuration file {path} does not exist", file=sys.stderr
        )
        return 2

    parser = build_parser(values)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "config":
        return run_config(path, values)
    if args.command == "download":
        options = (
            args.output,
            args.cookies_from_browser,
            args.format,
            args.lyrics,
            args.template,
        )
        if (args.link is None) == (args.input is None):
            parser.error("give one LINK or one --input FILE")
        if args.input is None:
            return run_download(args.link, *options)
        try:
            links = read_input(args.input)
        except (OSError, UnicodeDecodeError) as error:
            print(f"tunehound: cannot read {args.input}: {error}", file=sys.stderr)
            return 2
        if not links:
            print(f"tunehound: {args.input} has no links", file=sys.stderr)
            return 2
        return run_download_many(links, *options)
    parser.error(f"unknown command: {args.command}")
