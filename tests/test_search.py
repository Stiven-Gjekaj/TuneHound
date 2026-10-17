from tunehound.search import query_for, search_youtube
from tunehound.track import Track

TRACK = Track(
    title="A Song",
    artists=("First", "Second"),
    duration_ms=200000,
    source_url="https://example.invalid/track/1",
)


def test_query_for_names_the_artists_and_the_title():
    assert query_for(TRACK) == "First, Second - A Song"


def test_search_youtube_asks_for_the_limit_and_the_query():
    asked = []

    def extract(url):
        asked.append(url)
        return {"entries": []}

    assert search_youtube(TRACK, limit=3, extract=extract) == []
    assert asked == ["ytsearch3:First, Second - A Song"]


def test_search_youtube_makes_candidates_from_the_entries():
    entries = [
        {"id": "a", "title": "A Song", "channel": "First - Topic", "duration": 201},
        {"id": "b", "title": "A Song (Live)", "uploader": "Fan", "duration": None},
        {"id": "c", "title": "No channel"},
    ]
    found = search_youtube(TRACK, extract=lambda url: {"entries": entries})
    assert [(c.video_id, c.channel, c.duration_seconds) for c in found] == [
        ("a", "First - Topic", 201.0),
        ("b", "Fan", None),
        ("c", "", None),
    ]
    assert all(c.source == "youtube" for c in found)


def test_search_youtube_skips_broken_entries():
    entries = [None, {"id": "x"}, {"title": "no id"}, {"id": "y", "title": "Y"}]
    found = search_youtube(TRACK, extract=lambda url: {"entries": entries})
    assert [c.video_id for c in found] == ["y"]
