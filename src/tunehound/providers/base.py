"""The parts that all providers share."""

from dataclasses import dataclass
from typing import Protocol

from tunehound.track import Track


class ProviderError(Exception):
    """Tell that a provider cannot read a link or a page."""


@dataclass(frozen=True)
class TrackList:
    """Hold the songs of an album or a playlist."""

    kind: str
    name: str
    track_links: tuple[str, ...]
    cut_limit: int | None = None

    @property
    def album(self) -> str | None:
        """Return the album name for an album, and None for a playlist."""
        return self.name if self.kind == "album" else None

    @property
    def maybe_cut(self) -> bool:
        """Tell if the provider can have cut the list."""
        return self.cut_limit is not None and len(self.track_links) >= self.cut_limit


class Provider(Protocol):
    """Read songs from the links of one service."""

    name: str

    def owns(self, link: str) -> bool:
        """Tell if the link belongs to this provider."""
        ...

    def kind_of(self, link: str) -> str:
        """Return "track", "album", or "playlist"."""
        ...

    def fetch_track(self, link: str) -> Track:
        """Read the metadata of the song of a track link."""
        ...

    def fetch_list(self, link: str) -> TrackList:
        """Read the songs of an album or playlist link."""
        ...
