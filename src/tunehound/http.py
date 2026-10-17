"""Get pages and files over HTTP."""

import urllib.request

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TuneHound"
TIMEOUT_SECONDS = 20


def get_bytes(url: str) -> bytes:
    """Download the body of a URL."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def get_text(url: str) -> str:
    """Download the body of a URL as UTF-8 text."""
    return get_bytes(url).decode("utf-8")
