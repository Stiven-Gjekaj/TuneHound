# Changelog

Every release is written here, newest first. A version is
`MAJOR.MINOR.PATCH`. Before 1.0.0, each big addition raises the minor number.
From 1.0.0, a fix raises the patch number, a new function raises the minor
number, and a change that breaks the command line or the file names raises
the major number.
Each release on GitHub has the wheel and the source archive as assets.

## 1.1.1 (2026-10-17)

Better matches. In a test with 6 playlists, these fixes found 31 more of
281 songs, and 264 came through in all.

- TuneHound installs the YouTube challenge solver of yt-dlp, with the
  `yt-dlp[default]` extra. Without it, YouTube gave no audio formats when
  the request had a browser sign-in.
- A remix, a cover, or a slowed version on a channel of one of the artists
  of the track is the song itself, so TuneHound accepts it. Every artist of
  the track counts, not only the first.
- When a YouTube search gives no results, TuneHound searches again with the
  title first, and then with the title alone. YouTube gave no results for
  some search texts that start with a rare artist name.
- A result may differ from the track by 15 seconds at most, not 30. In the
  test, the right songs were within 8 seconds, and the wrong versions were
  21 to 29 seconds away.

## 1.1.0 (2026-10-17)

Full Spotify playlists.

- `--input FILE` reads one link or search text from each line of a text
  file. Empty lines and lines that start with `#` do not count. A line that
  fails does not stop the other lines. Copy the track links of a playlist
  from the Spotify desktop app into a file to get a playlist of more than
  100 songs with no keys.
- With the client ID and the client secret of a Spotify developer app,
  TuneHound reads the Spotify Web API. It gives every song of a public
  playlist or album, page by page, and the album, the track and disc
  numbers, and the ISRC of each song. Put the keys in the configuration file
  or in `TUNEHOUND_SPOTIFY_CLIENT_ID` and `TUNEHOUND_SPOTIFY_CLIENT_SECRET`.
  `tunehound config` says which way TuneHound reads Spotify, and it hides
  the secret. This code has unit tests, but it has not run against the live
  Spotify API, because no keys were available for a test.
- Each song line prints at once, so the lines keep their order when the
  output goes to a file or a pipe.

## 1.0.0 (2026-10-17)

The first full release. TuneHound is a command line tool only.

- The terminal user interface is gone, with the `tui` command and the
  Textual dependency. Use `tunehound download`.
- `--template` sets the path of each file, for example
  `"{artist}/{album}/{track_number:02} {title}"`. A slash makes a folder. A
  bad template stops the command before a download starts.
- A TOML configuration file holds the defaults: `output`, `format`,
  `lyrics`, `template`, and `cookies_from_browser`. `tunehound config` shows
  its path and its values. `--config FILE` and `TUNEHOUND_CONFIG` give
  another path. A value on the command line wins.
- `--no-lyrics` turns off the lyrics of the configuration file for one
  command.
- Install with `uv tool install` or `pipx install` from GitHub.
- The hand check in [docs/roadmap.md](docs/roadmap.md) passed for Spotify,
  Apple Music, SoundCloud, Bandcamp, and YouTube links. The Deezer and
  search downloads stopped at the YouTube sign-in check on the test machine.

## 0.5.0 (2026-10-17)

The terminal user interface downloads.

- `tunehound tui` downloads each link or search that you paste, at once.
  Up to three links run at the same time.
- Each row shows "searching", then the progress in percent, then the
  result. An album or a playlist gets one row for the list, with a count,
  and one row for each song.
- The status line counts the waiting, active, done, and failed rows, and
  shows the last error.
- `tunehound tui` takes the same options as `download`: `-o`, `--format`,
  `--lyrics`, and `--cookies-from-browser`.
- The columns of the queue fit the width of the screen. Before, a long link
  pushed the status out of the screen.

## 0.4.0 (2026-10-17)

Formats and full tags.

- `--format` chooses mp3, m4a, opus, or flac. Each format gets its own tags
  and the cover. A file of a different format does not count as already
  there.
- When a track has no album, no track number, or no ISRC, TuneHound fills
  them from Deezer. It uses the ISRC when the track has one. It fills
  nothing when no Deezer result has the same release date, because Deezer
  search often gives a compilation and not the original.
- `--lyrics` writes the lyrics from lrclib.net into the tags. A song with no
  lyrics there, or a lyrics stub of fewer than 20 characters, gets no
  lyrics. A failed lyrics request does not stop the song.

## 0.3.0 (2026-10-17)

More providers.

- Deezer track, album, and playlist links, from the public Deezer API. Short
  `link.deezer.com` links work too. A Deezer song gets the album, the track
  number, the disc number, the ISRC, and a cover of 1000 pixels.
- Apple Music song and album links, from the iTunes lookup API. An album
  downloads in the order of its discs.
- A plain search text, for example `"artist - title"`, finds the first song
  on Deezer.
- YouTube, YouTube Music, SoundCloud, and Bandcamp links go to yt-dlp with
  no match step. Playlists of YouTube and SoundCloud, and Bandcamp albums,
  work too.
- The disc number goes into the tags.
- A cover that is not a JPEG or a PNG image is left out. Before, it could
  stop the song.

## 0.2.0 (2026-10-17)

Albums and playlists.

- `tunehound download` takes Spotify album and playlist links, and downloads
  each song, one after the other.
- A song from an album link gets the album name and the track number as
  tags.
- When the file of a song is already in the folder, TuneHound skips it. Run
  the same command again to get the songs that failed.
- One line for each song, and a summary at the end. The command exits with 1
  when a song fails, and a failed song does not stop the other songs.
- A warning when a list has 100 songs, because the Spotify embed page can cut
  a list there.
- The errors of yt-dlp are short. When YouTube asks for a sign-in, the error
  says to use `--cookies-from-browser`.

## 0.1.0 (2026-10-17)

The first release. One song from a Spotify link.

- `tunehound download LINK` reads a Spotify track link, finds the same song
  on YouTube, downloads the audio with yt-dlp, and converts it to mp3.
- The file gets the title, the artists, the release date, the cover, and the
  link of the source as ID3 tags.
- The match scores each YouTube result by the title, the artist, the length,
  and the channel. It refuses a live version, a remix, or a cover when the
  track is not one, and it prefers the channel of the artist.
- `--cookies-from-browser` lets yt-dlp use the YouTube sign-in of a browser,
  for when YouTube asks for a sign-in.
- `tunehound tui` opens the first screen of the terminal user interface. It
  keeps a queue of links but does not download yet.
