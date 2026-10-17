"""The providers that give the metadata of a song."""

from tunehound.providers.base import Provider, ProviderError, TrackList
from tunehound.providers.spotify import SpotifyProvider

PROVIDERS: tuple[Provider, ...] = (SpotifyProvider(),)

__all__ = ["PROVIDERS", "Provider", "ProviderError", "TrackList", "find_provider"]


def find_provider(link: str, providers: tuple[Provider, ...] = PROVIDERS) -> Provider:
    """Return the provider that owns a link."""
    for provider in providers:
        if provider.owns(link):
            return provider
    raise ProviderError(f"TuneHound does not know this link: {link.strip()}")
