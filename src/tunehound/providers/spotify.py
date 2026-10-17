"""Read songs from Spotify links."""

import re

_ID = r"[0-9A-Za-z]{22}"
_URL_PATTERN = re.compile(
    rf"^https?://open\.spotify\.com/(?:intl-[a-z]{{2}}(?:-[a-z]{{2}})?/)?"
    rf"(?:embed/)?track/(?P<id>{_ID})(?:[/?#].*)?$"
)
_URI_PATTERN = re.compile(rf"^spotify:track:(?P<id>{_ID})$")


class SpotifyError(Exception):
    """Tell that a Spotify link or page is not usable."""


def parse_track_id(link: str) -> str:
    """Return the track ID in a Spotify link or URI."""
    link = link.strip()
    for pattern in (_URL_PATTERN, _URI_PATTERN):
        match = pattern.match(link)
        if match:
            return match.group("id")
    raise SpotifyError(f"not a Spotify track link: {link}")
