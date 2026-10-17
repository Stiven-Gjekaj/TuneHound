from tunehound.enrich import enrich, find_on_deezer, is_complete
from tunehound.track import Track

BARE = Track(
    title="A Song",
    artists=("Main",),
    duration_ms=211500,
    source_url="https://open.spotify.com/track/x",
    release_date="1987-11-12",
)


def deezer_track(**changes):
    data = {
        "id": 9,
        "title": "A Song",
        "duration": 211,
        "track_position": 3,
        "disk_number": 1,
        "isrc": "GBXXX0000001",
        "release_date": "1987-11-12",
        "artist": {"name": "Main"},
        "album": {"title": "An Album", "cover_xl": "https://img.invalid/1000"},
    }
    data.update(changes)
    return data


def search_answer(*items):
    return {"data": list(items), "total": len(items)}


def item(item_id, title="A Song", artist="Main", duration=211):
    return {
        "id": item_id,
        "title": title,
        "artist": {"name": artist},
        "duration": duration,
    }


def test_enrich_fills_only_the_empty_fields():
    def get_json(url):
        if "search" in url:
            return search_answer(item(9))
        return deezer_track()

    track = enrich(BARE, get_json)
    assert track.album == "An Album"
    assert (track.track_number, track.disc_number) == (3, 1)
    assert track.isrc == "GBXXX0000001"
    assert track.cover_url == "https://img.invalid/1000"
    assert track.release_date == "1987-11-12"
    assert track.title == BARE.title
    assert track.source_url == BARE.source_url


def test_find_on_deezer_checks_the_title_the_artist_and_the_length():
    asked = []

    def get_json(url):
        asked.append(url)
        if "search" in url:
            return search_answer(
                item(1, title="A Song (Live)"),
                item(2, artist="Other"),
                item(3, duration=260),
                item(4),
            )
        return deezer_track(id=4)

    found = find_on_deezer(BARE, get_json)
    assert found.source_url == "https://www.deezer.com/track/4"
    assert asked == [
        "https://api.deezer.com/search?q=Main%20A%20Song&limit=5",
        "https://api.deezer.com/track/4",
    ]


def test_find_on_deezer_uses_the_isrc_when_the_track_has_one():
    asked = []
    track = Track("A Song", ("Main",), 211000, "x", isrc="GBXXX0000001")

    def get_json(url):
        asked.append(url)
        return deezer_track()

    assert find_on_deezer(track, get_json).album == "An Album"
    assert asked == ["https://api.deezer.com/track/isrc:GBXXX0000001"]


def test_find_on_deezer_gives_none_for_an_unknown_isrc():
    track = Track("A Song", ("Main",), 211000, "x", isrc="NONE")
    answer = {"error": {"message": "no data"}}
    assert find_on_deezer(track, lambda url: answer) is None


def test_enrich_keeps_the_track_when_nothing_matches():
    assert enrich(BARE, lambda url: search_answer(item(1, title="Else"))) is BARE


def test_enrich_keeps_the_track_when_the_network_fails():
    def get_json(url):
        raise OSError("offline")

    assert enrich(BARE, get_json) is BARE


def test_enrich_does_not_ask_for_a_complete_track():
    full = Track(
        "A Song",
        ("Main",),
        1,
        "x",
        album="A",
        track_number=1,
        disc_number=1,
        isrc="I",
        release_date="2000-01-01",
        cover_url="c",
    )
    assert is_complete(full)
    assert enrich(full, lambda url: (_ for _ in ()).throw(AssertionError)) is full


def test_find_on_deezer_prefers_the_result_with_the_same_release_date():
    tracks = {
        "1": deezer_track(id=1, release_date="2008-01-01", album={"title": "Hits"}),
        "2": deezer_track(id=2, release_date="1987-11-12", album={"title": "Original"}),
    }

    def get_json(url):
        if "search" in url:
            return search_answer(item(1), item(2))
        return tracks[url.rsplit("/", 1)[1]]

    assert find_on_deezer(BARE, get_json).album == "Original"


def test_find_on_deezer_gives_none_when_no_date_agrees():
    def get_json(url):
        if "search" in url:
            return search_answer(item(1), item(2))
        track_id = int(url.rsplit("/", 1)[1])
        return deezer_track(id=track_id, release_date="2010-01-01")

    assert find_on_deezer(BARE, get_json) is None


def test_find_on_deezer_takes_the_first_match_without_a_release_date():
    bare = Track("A Song", ("Main",), 211500, "x")

    def get_json(url):
        if "search" in url:
            return search_answer(item(1), item(2))
        track_id = int(url.rsplit("/", 1)[1])
        return deezer_track(id=track_id, album={"title": f"A{track_id}"})

    assert find_on_deezer(bare, get_json).album == "A1"
