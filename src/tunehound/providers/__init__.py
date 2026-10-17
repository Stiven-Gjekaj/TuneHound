"""The providers that give the metadata of a song."""

from tunehound.providers.apple import AppleMusicProvider
from tunehound.providers.base import Provider, ProviderError, TrackList
from tunehound.providers.deezer import DeezerProvider
from tunehound.providers.direct import DirectProvider
from tunehound.providers.spotify import SpotifyProvider
from tunehound.providers.text import TextSearchProvider

PROVIDERS: tuple[Provider, ...] = (
    SpotifyProvider(),
    DeezerProvider(),
    AppleMusicProvider(),
    DirectProvider(),
    # The search goes last, because it owns every text that is not a link.
    TextSearchProvider(),
)

__all__ = [
    "PROVIDERS",
    "Provider",
    "ProviderError",
    "TrackList",
    "find_provider",
    "use_spotify_api",
]


def use_spotify_api(client_id: str, client_secret: str) -> None:
    """Let the Spotify provider read the Spotify Web API with these keys."""
    from tunehound.providers.spotify_api import SpotifyApi

    for provider in PROVIDERS:
        if isinstance(provider, SpotifyProvider):
            provider.api = SpotifyApi(client_id, client_secret)


def find_provider(link: str, providers: tuple[Provider, ...] = PROVIDERS) -> Provider:
    """Return the provider that owns a link."""
    for provider in providers:
        if provider.owns(link):
            return provider
    raise ProviderError(f"TuneHound does not know this link: {link.strip()}")
