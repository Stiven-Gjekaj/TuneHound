from pathlib import Path

import pytest

from tunehound.naming import (
    DEFAULT_TEMPLATE,
    TemplateError,
    check_template,
    render,
    safe_filename,
)
from tunehound.track import Track

TRACK = Track(
    title="Back In Black",
    artists=("AC/DC", "Guest"),
    duration_ms=1000,
    source_url="x",
    album="Back In Black",
    track_number=6,
    disc_number=1,
    release_date="1980-07-25",
)


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("AC/DC - Back In Black", "AC_DC - Back In Black"),
        ('What? "Yes" <No> | a*b \\ c:d', "What_ _Yes_ _No_ _ a_b _ c_d"),
        ("  lots   of\tspace  ", "lots of space"),
        ("ends with dots...", "ends with dots"),
        ("...", "track"),
        ("a" * 300, "a" * 200),
    ],
)
def test_safe_filename_removes_unsafe_characters(text, name):
    assert safe_filename(text) == name


def test_render_uses_the_default_template():
    assert render(DEFAULT_TEMPLATE, TRACK) == Path("AC_DC - Back In Black")


def test_render_makes_folders_from_slashes():
    template = "{artist}/{album} ({year})/{disc_number}-{track_number:02} {title}"
    assert render(template, TRACK) == Path(
        "AC_DC", "Back In Black (1980)", "1-06 Back In Black"
    )


def test_render_fills_the_missing_values():
    bare = Track("Song", ("Main",), 1000, "x")
    assert render("{album}/{year}/{track_number:02} {title}", bare) == Path(
        "Unknown Album", "Unknown Year", "00 Song"
    )


def test_render_names_all_the_artists():
    assert render("{artists} - {title}", TRACK) == Path("AC_DC, Guest - Back In Black")


def test_render_skips_empty_parts():
    assert render("/{artist}//{title}/", TRACK) == Path("AC_DC", "Back In Black")


@pytest.mark.parametrize(
    "template",
    ["", "   ", "{genre} - {title}", "{title", "{track_number:zz}", "/"],
)
def test_check_template_refuses_a_bad_template(template):
    with pytest.raises(TemplateError):
        check_template(template)


def test_check_template_accepts_every_field():
    check_template(
        "{artist}{artists}{title}{album}{track_number:02}{disc_number}{year}"
    )
