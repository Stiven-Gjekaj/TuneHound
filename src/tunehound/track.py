"""The metadata of one song."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    """Hold the metadata that a provider gives for one song."""

    title: str
    artists: tuple[str, ...]
    duration_ms: int
    source_url: str
    album: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    release_date: str | None = None
    isrc: str | None = None
    cover_url: str | None = None
    explicit: bool = False

    @property
    def artist(self) -> str:
        """Return all artists as one string."""
        return ", ".join(self.artists)

    @property
    def duration_seconds(self) -> float:
        """Return the length in seconds."""
        return self.duration_ms / 1000

    @property
    def year(self) -> str | None:
        """Return the year of the release date."""
        if not self.release_date:
            return None
        return self.release_date[:4]
