"""Make the path of an audio file from a template.

A template is a text with fields in braces, for example
"{artist}/{album}/{track_number:02} - {title}". A slash makes a folder.
"""

import re
import string
from pathlib import Path

from tunehound.track import Track

DEFAULT_TEMPLATE = "{artist} - {title}"
MAX_PART_LENGTH = 200
FIELDS = ("artist", "artists", "title", "album", "track_number", "disc_number", "year")
_UNSAFE = re.compile(r'[\x00-\x1f<>:"/\\|?*]')


class TemplateError(ValueError):
    """Tell that a file name template is not usable."""


def safe_filename(text: str) -> str:
    """Make text safe to use as a file name on Windows, macOS, and Linux."""
    name = _UNSAFE.sub("_", " ".join(text.split())).strip(" .")
    return name[:MAX_PART_LENGTH].rstrip(" .") or "track"


def _values(track: Track) -> dict[str, object]:
    return {
        "artist": track.artists[0],
        "artists": track.artist,
        "title": track.title,
        "album": track.album or "Unknown Album",
        "track_number": track.track_number or 0,
        "disc_number": track.disc_number or 0,
        "year": track.year or "Unknown Year",
    }


def check_template(template: str) -> None:
    """Raise TemplateError when a template has an unknown field or bad syntax."""
    if not template.strip():
        raise TemplateError("the file name template is empty")
    try:
        names = [name for _, name, _, _ in string.Formatter().parse(template) if name]
    except ValueError as error:
        raise TemplateError(f"the file name template is not valid: {error}") from error
    for name in names:
        if name not in FIELDS:
            known = ", ".join(FIELDS)
            raise TemplateError(
                f"unknown field {{{name}}} in the template. Use: {known}"
            )
    sample = Track("t", ("a",), 0, "x", track_number=1, disc_number=1)
    render(template, sample)


def render(template: str, track: Track) -> Path:
    """Return the relative path, with no suffix, of the file of a track."""
    values = _values(track)
    parts = []
    for part in template.split("/"):
        if not part.strip():
            continue
        try:
            text = part.format_map(values)
        except (KeyError, ValueError, IndexError) as error:
            raise TemplateError(
                f"cannot use the template part {part!r}: {error}"
            ) from error
        parts.append(safe_filename(text))
    if not parts:
        raise TemplateError("the file name template gives no file name")
    return Path(*parts)
