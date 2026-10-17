from tunehound.track import Track


def make_track(**changes):
    values = {
        "title": "Song",
        "artists": ("First", "Second"),
        "duration_ms": 213573,
        "source_url": "https://example.invalid/track/1",
    }
    values.update(changes)
    return Track(**values)


def test_artist_joins_all_artists():
    assert make_track().artist == "First, Second"


def test_duration_seconds_converts_milliseconds():
    assert make_track().duration_seconds == 213.573


def test_year_comes_from_the_release_date():
    assert make_track(release_date="1987-11-12").year == "1987"


def test_year_is_none_without_a_release_date():
    assert make_track().year is None
