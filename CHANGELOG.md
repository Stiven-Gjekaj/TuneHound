# Changelog

Every release is written here, newest first. A version is
`MAJOR.MINOR.PATCH`. Before 1.0.0, each big addition raises the minor number.
From 1.0.0, a fix raises the patch number, a new function raises the minor
number, and a change that breaks the command line or the file names raises
the major number.
Each release on GitHub has the wheel and the source archive as assets.

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
