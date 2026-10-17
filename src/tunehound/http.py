"""Get pages and files over HTTP."""

import json
import urllib.parse
import urllib.request
from typing import Any

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


def get_json(url: str) -> Any:
    """Download the body of a URL and read it as JSON."""
    return json.loads(get_bytes(url))


def final_url(url: str) -> str:
    """Follow the redirects of a URL and return the last URL."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.geturl()


def request_json(
    url: str,
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
) -> Any:
    """Send a request and read the answer as JSON.

    With `form`, the request is a POST with a form body. Else it is a GET.
    """
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    request = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read())
