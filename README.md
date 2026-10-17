# TuneHound

TuneHound downloads music from many providers.
It reads the metadata of a track, an album, or a playlist from the provider.
It finds the same song on a public source and downloads it with yt-dlp.
Then it converts the audio with ffmpeg and writes the tags.

TuneHound does not decrypt DRM streams.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) on your `PATH`

## Install for development

    uv sync

## Use

Show the help:

    uv run tunehound --help

Open the terminal user interface:

    uv run tunehound tui

Press `q` to close it.

## Test

    uv run pytest
    uv run ruff check .
