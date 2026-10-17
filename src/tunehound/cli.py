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
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    commands.add_parser("tui", help="open the terminal user interface")
    return parser


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
    parser.error(f"unknown command: {args.command}")
