from tunehound.search import queries_for, query_for, search_youtube
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
    assert asked[0] == "ytsearch3:First, Second - A Song"


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


def test_queries_for_puts_the_title_first_in_the_second_text():
    assert queries_for(TRACK) == [
        "First, Second - A Song",
        "A Song First, Second",
        "A Song",
    ]


def test_search_youtube_tries_the_next_text_when_there_are_no_results():
    asked = []
    entry = {"id": "a", "title": "A Song", "channel": "First", "duration": 200}

    def extract(url):
        asked.append(url)
        if url.endswith("A Song First, Second"):
            return {"entries": [entry]}
        return {"entries": []}

    found = search_youtube(TRACK, limit=5, extract=extract)
    assert [c.video_id for c in found] == ["a"]
    assert asked == [
        "ytsearch5:First, Second - A Song",
        "ytsearch5:A Song First, Second",
    ]


def test_search_youtube_stops_at_the_first_text_with_results():
    asked = []

    def extract(url):
        asked.append(url)
        return {"entries": [{"id": "a", "title": "x"}]}

    search_youtube(TRACK, extract=extract)
    assert len(asked) == 1
