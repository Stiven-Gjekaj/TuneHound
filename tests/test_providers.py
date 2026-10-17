import pytest

from tunehound.providers import ProviderError, find_provider


class OwnsPrefix:
    def __init__(self, prefix):
        self.name = prefix
        self.prefix = prefix

    def owns(self, link):
        return link.startswith(self.prefix)


def test_find_provider_returns_the_first_owner():
    providers = (OwnsPrefix("a"), OwnsPrefix("ab"))
    assert find_provider("abc", providers).name == "a"
    assert find_provider("b", (OwnsPrefix("a"), OwnsPrefix("b"))).name == "b"


def test_find_provider_refuses_an_unknown_link():
    with pytest.raises(ProviderError, match="does not know this link"):
        find_provider(" https://example.com/x ", (OwnsPrefix("a"),))


def test_find_provider_knows_spotify_by_default():
    assert find_provider("spotify:track:" + "a" * 22).name == "spotify"


def test_find_provider_knows_deezer_by_default():
    assert find_provider("https://www.deezer.com/track/1").name == "deezer"


def test_find_provider_knows_apple_music_by_default():
    assert find_provider("https://music.apple.com/us/song/1").name == "apple"
