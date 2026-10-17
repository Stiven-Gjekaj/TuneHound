"""The providers that give the metadata of a song."""

from tunehound.providers.apple import AppleMusicProvider
from tunehound.providers.base import Provider, ProviderError, TrackList
from tunehound.providers.deezer import DeezerProvider
from tunehound.providers.spotify import SpotifyProvider
from tunehound.providers.text import TextSearchProvider

PROVIDERS: tuple[Provider, ...] = (
    SpotifyProvider(),
    DeezerProvider(),
    AppleMusicProvider(),
    # The search goes last, because it owns every text that is not a link.
    TextSearchProvider(),
)

__all__ = ["PROVIDERS", "Provider", "ProviderError", "TrackList", "find_provider"]


def find_provider(link: str, providers: tuple[Provider, ...] = PROVIDERS) -> Provider:
    """Return the provider that owns a link."""
    for provider in providers:
        if provider.owns(link):
            return provider
    raise ProviderError(f"TuneHound does not know this link: {link.strip()}")
