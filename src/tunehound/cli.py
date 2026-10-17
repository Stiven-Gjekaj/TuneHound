"""The command line interface of TuneHound."""

import argparse
from collections.abc import Sequence

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
    parser.add_subparsers(dest="command", metavar="COMMAND")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return 0
