"""Read the defaults of the command line from a TOML configuration file.

The file is optional. A value on the command line wins over a value in the
file. An example file:

    output = "~/Music"
    format = "flac"
    lyrics = true
    template = "{artist}/{album}/{track_number:02} {title}"
    cookies_from_browser = "firefox"
    spotify_client_id = "..."
    spotify_client_secret = "..."

The two Spotify keys can also come from the environment variables
TUNEHOUND_SPOTIFY_CLIENT_ID and TUNEHOUND_SPOTIFY_CLIENT_SECRET. The
environment wins over the file.
"""

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from tunehound.download import CODECS
from tunehound.naming import TemplateError, check_template

ENVIRONMENT_VARIABLE = "TUNEHOUND_CONFIG"
KEYS = (
    "output",
    "format",
    "lyrics",
    "template",
    "cookies_from_browser",
    "spotify_client_id",
    "spotify_client_secret",
)
SECRET_KEYS = ("spotify_client_secret",)
SPOTIFY_ENVIRONMENT = {
    "spotify_client_id": "TUNEHOUND_SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "TUNEHOUND_SPOTIFY_CLIENT_SECRET",
}


class ConfigError(Exception):
    """Tell that the configuration file is not usable."""


def default_path() -> Path:
    """Return the path of the configuration file for this system."""
    if os.environ.get(ENVIRONMENT_VARIABLE):
        return Path(os.environ[ENVIRONMENT_VARIABLE]).expanduser()
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "tunehound" / "config.toml"


def _check(key: str, value: Any) -> Any:
    if key == "output":
        if not isinstance(value, str) or not value.strip():
            raise ConfigError("output must be the text of a folder")
        return Path(value).expanduser()
    if key == "format":
        if value not in CODECS:
            raise ConfigError(f"format must be one of: {', '.join(CODECS)}")
        return value
    if key == "lyrics":
        if not isinstance(value, bool):
            raise ConfigError("lyrics must be true or false")
        return value
    if key == "template":
        if not isinstance(value, str):
            raise ConfigError("template must be a text")
        try:
            check_template(value)
        except TemplateError as error:
            raise ConfigError(str(error)) from error
        return value
    if key in SPOTIFY_ENVIRONMENT:
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{key} must be a text")
        return value.strip()
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("cookies_from_browser must be the name of a browser")
    return value


def load(path: Path) -> dict[str, Any]:
    """Return the checked values of a configuration file.

    A missing file gives no values.
    """
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    values = {}
    for key, value in data.items():
        if key not in KEYS:
            raise ConfigError(f"unknown key {key!r} in {path}. Use: {', '.join(KEYS)}")
        try:
            values[key] = _check(key, value)
        except ConfigError as error:
            raise ConfigError(f"{path}: {error}") from error
    return values


def spotify_keys(values: dict[str, Any]) -> tuple[str, str] | None:
    """Return the Spotify client ID and secret, or None when there are none.

    The environment wins over the values of the file. Give both keys or
    neither.
    """
    keys = {
        key: os.environ.get(variable, "").strip() or values.get(key)
        for key, variable in SPOTIFY_ENVIRONMENT.items()
    }
    client_id = keys["spotify_client_id"]
    client_secret = keys["spotify_client_secret"]
    if not client_id and not client_secret:
        return None
    if not client_id or not client_secret:
        raise ConfigError("give both spotify_client_id and spotify_client_secret")
    return client_id, client_secret


def shown(key: str, value: Any) -> str:
    """Return a value as text, with a secret hidden."""
    if key in SECRET_KEYS:
        return "(hidden)"
    return str(value)
