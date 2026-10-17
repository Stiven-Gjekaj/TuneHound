<div align="center">

![TuneHound](assets/wordmark.svg)

### Finds a song and downloads it

_Paste a link. TuneHound finds the song, downloads it, and tags it._

![Python](https://img.shields.io/badge/python_3.11+-22d3ee?style=for-the-badge&logo=python&logoColor=070b14)
![ffmpeg](https://img.shields.io/badge/ffmpeg-60a5fa?style=for-the-badge&logo=ffmpeg&logoColor=070b14)
![yt-dlp](https://img.shields.io/badge/yt--dlp-a78bfa?style=for-the-badge&logo=youtube&logoColor=070b14)
![Spotify](https://img.shields.io/badge/spotify-f472b6?style=for-the-badge&logo=spotify&logoColor=070b14)
[![MIT licence](https://img.shields.io/badge/mit_licence-fce7f3?style=for-the-badge&logoColor=070b14)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Stiven-Gjekaj/TuneHound?style=for-the-badge&label=release&labelColor=e0e7ff&color=e0e7ff)](https://github.com/Stiven-Gjekaj/TuneHound/releases/latest)

<p align="center">
  <a href="#overview"><b>Overview</b></a> |
  <a href="#use"><b>Use</b></a> |
  <a href="#what-works-now"><b>What works</b></a> |
  <a href="docs/roadmap.md"><b>Roadmap</b></a> |
  <a href="CHANGELOG.md"><b>Changelog</b></a>
</p>

</div>

---

> [!NOTE]
> **Version 1.0.0 is out.**
> It downloads songs, albums, and playlists from Spotify, Deezer, Apple
> Music, YouTube, SoundCloud, and Bandcamp links, or from a search text, as
> mp3, m4a, opus, or flac, with full tags, lyrics on request, a file name
> template, and a configuration file.
> [Install](#install) says how to get it, and
> [the roadmap](docs/roadmap.md) holds the hand check of this version.

## Overview

TuneHound downloads music from many providers.
It reads the metadata of a song from Spotify, Deezer, or Apple Music.
It finds the same song on YouTube and downloads it with yt-dlp.
Then it converts the audio to mp3 with ffmpeg and writes the tags and the
cover.
A YouTube, SoundCloud, or Bandcamp link already points at the audio, so
TuneHound downloads it as it is.

TuneHound does not decrypt DRM streams.

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) on your `PATH`

## Install

With uv:

    uv tool install git+https://github.com/Stiven-Gjekaj/TuneHound@v1.0.0

Or with pipx:

    pipx install git+https://github.com/Stiven-Gjekaj/TuneHound@v1.0.0

Then run `tunehound` with no `uv run` in front.

## Install for development

    uv sync

## Use

Download one song from a Spotify link into the current folder:

    uv run tunehound download https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC

Download every song of an album or a playlist:

    uv run tunehound download https://open.spotify.com/album/6eUW0wxWtzkFdaEFsTJto6

TuneHound prints one line for each song and a summary at the end. A song
that fails does not stop the other songs. When the file of a song is already
in the folder, TuneHound skips the song, so you can run the same command
again to get the songs that failed.

The same command takes links of other providers, and plain search text:

    uv run tunehound download https://www.deezer.com/album/1416578
    uv run tunehound download "https://music.apple.com/us/album/3-originals/1559523357?i=1559523359"
    uv run tunehound download https://soundcloud.com/artist/song
    uv run tunehound download "rick astley never gonna give you up"

TuneHound finds a search text on Deezer and takes the first song.

Choose the audio format, and add the lyrics from lrclib.net:

    uv run tunehound download LINK --format flac --lyrics

The formats are mp3 (the default), m4a, opus, and flac. Each format gets
its own tags and the cover.

Put the files in a different folder:

    uv run tunehound download LINK -o ~/Music

YouTube sometimes asks for a sign-in to confirm that you are not a bot.
Then let yt-dlp use the YouTube sign-in of your browser:

    uv run tunehound download LINK --cookies-from-browser firefox

Choose the path of each file with a template. A slash makes a folder:

    uv run tunehound download LINK --template "{artist}/{album}/{track_number:02} {title}"

The fields are `{artist}`, `{artists}`, `{title}`, `{album}`,
`{track_number}`, `{disc_number}`, and `{year}`. A missing album becomes
"Unknown Album", a missing year becomes "Unknown Year", and a missing
number becomes 0.

Show the help:

    uv run tunehound --help

## Configuration

A configuration file holds your defaults. A value on the command line wins
over it. See where TuneHound looks for the file:

    uv run tunehound config

On macOS and Linux the file is `~/.config/tunehound/config.toml`. On
Windows it is `%APPDATA%\tunehound\config.toml`. The environment variable
`TUNEHOUND_CONFIG`, or the option `--config FILE`, gives another path.

    output = "~/Music"
    format = "flac"
    lyrics = true
    template = "{artist}/{album}/{track_number:02} {title}"
    cookies_from_browser = "firefox"

Use `--no-lyrics` to turn off the lyrics of the file for one command.

## What works now

| Link | Track | Album | Playlist | Match step |
| --- | --- | --- | --- | --- |
| Spotify | yes | yes | yes | yes |
| Deezer | yes | yes | yes | yes |
| Apple Music | yes | yes | no | yes |
| Search text | yes | no | no | yes |
| YouTube and YouTube Music | yes | no | yes | no |
| SoundCloud | yes | no | yes | no |
| Bandcamp | yes | yes | no | no |

- Tags: the title, the artists, the album, the track and disc numbers, the
  release date, the ISRC, the cover, and the link of the source, when the
  provider gives them. When a Spotify or Apple Music track has no album or
  ISRC, TuneHound fills them from Deezer, but only from a Deezer result with
  the same release date. Lyrics come from lrclib.net with `--lyrics`.
- Lists: the Spotify embed page gave 100 songs at most for a playlist in a
  test. TuneHound warns when a Spotify playlist has 100 songs, because songs
  can be missing.
- Formats: mp3, m4a, opus, and flac.
- Match: TuneHound searches YouTube and scores each result by the title, the
  artist, the length, and the channel. It refuses a live version, a remix, or
  a cover when the track is not one. YouTube Music search gives no songs in
  some countries, for example Albania, so TuneHound searches YouTube.

## Test

    scripts/check.sh
