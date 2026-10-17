"""Find the search result that is the same song as a track."""

import re
import unicodedata
from dataclasses import dataclass

from tunehound.track import Track

MAX_DURATION_DIFFERENCE = 30.0
MIN_TITLE_COVERAGE = 0.5
MIN_SCORE = 0.6

# A result with one of these words is a different version of the song,
# except when the title of the track has the word too.
OTHER_VERSION_WORDS = frozenset(
    {
        "8d",
        "acoustic",
        "cover",
        "instrumental",
        "karaoke",
        "live",
        "mashup",
        "nightcore",
        "reaction",
        "remix",
        "reverb",
        "slowed",
        "sped",
        "tutorial",
    }
)
OTHER_VERSION_PENALTY = 0.5
TOPIC_BONUS = 0.1
ARTIST_CHANNEL_BONUS = 0.05


@dataclass(frozen=True)
class Candidate:
    """Hold one search result."""

    video_id: str
    title: str
    channel: str
    duration_seconds: float | None
    source: str

    @property
    def url(self) -> str:
        """Return the watch URL of the result."""
        return f"https://www.youtube.com/watch?v={self.video_id}"


def normalize(text: str) -> str:
    """Make text lower case, with no accents and no punctuation."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w\s]", " ", text.casefold())
    return " ".join(text.split())


def _words(text: str) -> list[str]:
    return normalize(text).split()


def _coverage(needle: str, haystack: set[str]) -> float:
    words = _words(needle)
    if not words:
        return 0.0
    return sum(word in haystack for word in words) / len(words)


def score(track: Track, candidate: Candidate) -> float | None:
    """Return how well a result agrees with a track, or None to refuse it."""
    if candidate.duration_seconds is None:
        return None
    difference = abs(candidate.duration_seconds - track.duration_seconds)
    if difference > MAX_DURATION_DIFFERENCE:
        return None

    result_words = set(_words(candidate.title)) | set(_words(candidate.channel))
    title_coverage = _coverage(track.title, result_words)
    if title_coverage < MIN_TITLE_COVERAGE:
        return None
    artist_coverage = _coverage(track.artists[0], result_words)

    total = (
        0.4 * title_coverage
        + 0.3 * artist_coverage
        + 0.3 * (1 - difference / MAX_DURATION_DIFFERENCE)
    )

    channel = normalize(candidate.channel)
    artist = normalize(track.artists[0])
    if channel == f"{artist} topic":
        total += TOPIC_BONUS
    elif channel in (artist, f"{artist} vevo", f"{artist}vevo"):
        total += ARTIST_CHANNEL_BONUS

    track_words = set(_words(track.title))
    other_words = OTHER_VERSION_WORDS & set(_words(candidate.title)) - track_words
    return total - OTHER_VERSION_PENALTY * len(other_words)


def best_match(track: Track, candidates: list[Candidate]) -> Candidate | None:
    """Return the result that agrees best with a track, or None.

    When two results have the same score, the earlier result wins, because
    the search puts the more popular result first.
    """
    best: Candidate | None = None
    best_score = 0.0
    for candidate in candidates:
        value = score(track, candidate)
        if value is not None and value >= MIN_SCORE and value > best_score:
            best, best_score = candidate, value
    return best
