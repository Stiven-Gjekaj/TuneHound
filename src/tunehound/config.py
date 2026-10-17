"""Read the defaults of the command line from a TOML configuration file.

The file is optional. A value on the command line wins over a value in the
file. An example file:

    output = "~/Music"
    format = "flac"
    lyrics = true
    template = "{artist}/{album}/{track_number:02} {title}"
    cookies_from_browser = "firefox"
"""

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from tunehound.download import CODECS
from tunehound.naming import TemplateError, check_template

ENVIRONMENT_VARIABLE = "TUNEHOUND_CONFIG"
KEYS = ("output", "format", "lyrics", "template", "cookies_from_browser")


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
