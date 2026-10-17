import pytest

from tunehound.matching import Candidate, best_match, normalize, score
from tunehound.track import Track


def make_track(title="Monkeys Spinning Monkeys", artist="Kevin MacLeod", seconds=127):
    return Track(
        title=title,
        artists=(artist,),
        duration_ms=seconds * 1000,
        source_url="https://example.invalid/track/1",
    )


def make_candidate(title, channel="Someone", seconds=127.0, video_id="id"):
    return Candidate(
        video_id=video_id,
        title=title,
        channel=channel,
        duration_seconds=seconds,
        source="youtube",
    )


def test_normalize_removes_case_accents_and_punctuation():
    assert normalize("  Beyoncé - Halo (Official)!  ") == "beyonce halo official"


def test_candidate_url_is_the_watch_page():
    assert make_candidate("x", video_id="abc").url == (
        "https://www.youtube.com/watch?v=abc"
    )


def test_score_refuses_a_result_with_no_duration():
    assert (
        score(make_track(), make_candidate("Monkeys Spinning Monkeys", seconds=None))
        is None
    )


def test_score_refuses_a_result_that_is_much_longer():
    one_hour = make_candidate("Monkeys Spinning Monkeys [1 HOUR]", seconds=3600)
    assert score(make_track(), one_hour) is None


def test_score_refuses_a_result_with_another_title():
    assert score(make_track(), make_candidate("Kevin MacLeod - Sneaky Snitch")) is None


def test_score_prefers_the_topic_channel_of_the_artist():
    topic = make_candidate("Monkeys Spinning Monkeys", channel="Kevin MacLeod - Topic")
    upload = make_candidate("Monkeys Spinning Monkeys", channel="Kevin MacLeod")
    assert score(make_track(), topic) > score(make_track(), upload)


def test_score_prefers_a_closer_duration():
    close = make_candidate("Kevin MacLeod: Monkeys Spinning Monkeys", seconds=128)
    far = make_candidate("Kevin MacLeod: Monkeys Spinning Monkeys", seconds=150)
    assert score(make_track(), close) > score(make_track(), far)


@pytest.mark.parametrize("word", ["Live", "Remix", "Piano Tutorial", "Slowed"])
def test_score_lowers_another_version_of_the_song(word):
    plain = make_candidate("Kevin MacLeod - Monkeys Spinning Monkeys")
    other = make_candidate(f"Kevin MacLeod - Monkeys Spinning Monkeys ({word})")
    assert score(make_track(), other) < score(make_track(), plain)


def test_score_keeps_a_version_word_that_the_track_title_has():
    track = make_track(title="Song (Live)")
    live = make_candidate("Kevin MacLeod - Song (Live)")
    assert score(track, live) == score(
        track, make_candidate("Kevin MacLeod - Song Live")
    )


def test_best_match_picks_the_best_result():
    candidates = [
        make_candidate("Monkeys Spinning Monkeys [1 HOUR]", seconds=3750, video_id="a"),
        make_candidate(
            "Monkeys Spinning Monkeys - Piano Tutorial", seconds=134, video_id="b"
        ),
        make_candidate(
            "Kevin MacLeod: Monkeys Spinning Monkeys", seconds=131, video_id="c"
        ),
        make_candidate("Monkeys Spinning Monkeys", "Kevin MacLeod - Topic", 127, "d"),
    ]
    assert best_match(make_track(), candidates).video_id == "d"


def test_best_match_gives_none_when_no_result_is_good():
    candidates = [make_candidate("Something Else", seconds=127)]
    assert best_match(make_track(), candidates) is None


def test_best_match_gives_none_for_no_results():
    assert best_match(make_track(), []) is None
