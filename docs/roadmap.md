# Roadmap

This file tells what each release adds, up to 1.0.0.
[releasing.md](releasing.md) tells how to cut a release.

## 0.1.0: one song

- Read a Spotify track link from the embed page. This needs no account.
- Search YouTube with yt-dlp and score each result against the track.
- Download the audio with yt-dlp, convert it to mp3, and write the tags and
  the cover.
- A first screen for the terminal user interface.

## 0.2.0: albums and playlists

- Read Spotify album and playlist links.
- Download each song of a list, one after the other.
- Skip a song when its file is already in the folder.
- Show a short summary at the end: how many songs passed, were skipped, or
  failed.

## 0.3.0: more providers

- Deezer links for tracks, albums, and playlists, from the public API.
- Apple Music links for tracks and albums, from the iTunes lookup API.
- YouTube, YouTube Music, SoundCloud, and Bandcamp links go to yt-dlp
  directly, with no match step.
- A search text instead of a link finds the song on Deezer first.

## 0.4.0: formats and full tags

- The formats mp3, m4a, opus, and flac, each with its own tags.
- Find the album, the track number, the disc number, and the ISRC on Deezer
  when the provider does not give them. Use the ISRC for this when the track
  has one. Fill nothing when no Deezer result has the same release date,
  because Deezer search often gives a compilation and not the original.
- Write the lyrics from lrclib.net when the user asks for them.
- Not done: the ISRC does not help the match on YouTube, because the YouTube
  search results do not give an ISRC.

## 0.5.0: the terminal user interface downloads

- The screen runs the downloads that the user pastes.
- Each row shows its progress and its result.
- Downloads run at the same time, with a limit.

## 1.0.0: ready for use

- A configuration file for the output folder, the format, the file name
  template, and the browser for the sign-in.
- Install with `uv tool install` or `pipx install` from GitHub.
- A full hand check of every provider and every format on a real machine.
