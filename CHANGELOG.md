# Changelog

Every release is written here, newest first. A version is
`MAJOR.MINOR.PATCH`. Before 1.0.0, each big addition raises the minor number.
From 1.0.0, a fix raises the patch number, a new function raises the minor
number, and a change that breaks the command line or the file names raises
the major number.
Each release on GitHub has the wheel and the source archive as assets.

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
