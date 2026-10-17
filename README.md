# TuneHound

TuneHound downloads music from many providers.
It reads the metadata of a song from the provider.
It finds the same song on YouTube and downloads it with yt-dlp.
Then it converts the audio to mp3 with ffmpeg and writes the tags and the
cover.

TuneHound does not decrypt DRM streams.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) on your `PATH`

## Install for development

    uv sync

## Use

Download one song from a Spotify link into the current folder:

    uv run tunehound download https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC

Put the file in a different folder:

    uv run tunehound download LINK -o ~/Music

YouTube sometimes asks for a sign-in to confirm that you are not a bot.
Then let yt-dlp use the YouTube sign-in of your browser:

    uv run tunehound download LINK --cookies-from-browser firefox

Show the help:

    uv run tunehound --help

Open the terminal user interface:

    uv run tunehound tui

Press `q` to close it.

## What works now

- Providers: Spotify track links. Albums, playlists, and other providers
  come later.
- Tags: the title, the artists, the release date, the cover, and the link of
  the source. The Spotify embed page does not give the album or the ISRC.
- Format: mp3.
- Match: TuneHound searches YouTube and scores each result by the title, the
  artist, the length, and the channel. It refuses a live version, a remix, or
  a cover when the track is not one. YouTube Music search gives no songs in
  some countries, for example Albania, so TuneHound searches YouTube.

## Test

    uv run pytest
    uv run ruff check .
