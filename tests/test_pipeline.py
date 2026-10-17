import dataclasses
from pathlib import Path

import pytest

from tunehound.matching import Candidate
from tunehound.pipeline import (
    NoMatchError,
    Outcome,
    Result,
    download_link,
    download_track,
)
from tunehound.providers import TrackList
from tunehound.track import Track

TRACK = Track(
    title="Song: Part 1/2",
    artists=("First",),
    duration_ms=200000,
    source_url="https://open.spotify.com/track/x",
    cover_url="https://img.invalid/640",
)
GOOD = Candidate("good", "First - Song: Part 1/2", "First - Topic", 200.0, "youtube")
BAD = Candidate("bad", "Other Thing", "Someone", 200.0, "youtube")


def make_steps(candidates, cover=b"\xff\xd8\xffcover", cover_error=None):
    calls = {}

    def fetch(link):
        calls["link"] = link
        return TRACK

    def search(track):
        return candidates

    def download(url, stem, codec="mp3", cookies_from_browser=None, progress_hook=None):
        calls["download"] = (url, stem, cookies_from_browser)
        calls["codec"] = codec
        calls["progress_hook"] = progress_hook
        return stem.with_name(f"{stem.name}.{codec}")

    def get_bytes(url):
        calls["cover_url"] = url
        if cover_error:
            raise cover_error
        return cover

    def tag(path, track, cover_data, lyrics=None):
        calls["tag"] = (path, track, cover_data)
        calls["lyrics"] = lyrics

    steps = {
        "fill": lambda track: track,
        "fetch": fetch,
        "search": search,
        "download": download,
        "get_bytes": get_bytes,
        "tag": tag,
    }
    return steps, calls


def test_download_track_runs_all_steps_in_order(tmp_path):
    steps, calls = make_steps([BAD, GOOD])
    result = download_track("link", tmp_path, cookies_from_browser="firefox", **steps)

    stem = tmp_path / "First - Song_ Part 1_2"
    assert calls["link"] == "link"
    assert calls["download"] == (GOOD.url, stem, "firefox")
    assert calls["cover_url"] == "https://img.invalid/640"
    assert calls["tag"] == (Path(f"{stem}.mp3"), TRACK, b"\xff\xd8\xffcover")
    assert result.match == GOOD
    assert result.path == Path(f"{stem}.mp3")


def test_download_track_fails_when_nothing_matches(tmp_path):
    steps, calls = make_steps([BAD])
    with pytest.raises(NoMatchError):
        download_track("link", tmp_path, **steps)
    assert "download" not in calls


def test_download_track_tags_without_a_cover_when_the_cover_fails(tmp_path):
    steps, calls = make_steps([GOOD], cover_error=OSError("offline"))
    download_track("link", tmp_path, **steps)
    assert calls["tag"][2] is None


def test_download_track_skips_a_file_that_is_already_there(tmp_path):
    existing = tmp_path / "First - Song_ Part 1_2.mp3"
    existing.write_bytes(b"old audio")
    steps, calls = make_steps([GOOD])

    result = download_track("link", tmp_path, **steps)

    assert result.skipped is True
    assert result.path == existing
    assert result.match is None
    assert "download" not in calls
    assert "tag" not in calls
    assert existing.read_bytes() == b"old audio"


def test_download_track_sets_the_album_and_the_track_number(tmp_path):
    steps, calls = make_steps([GOOD])
    result = download_track("link", tmp_path, album="An Album", track_number=4, **steps)
    assert result.track.album == "An Album"
    assert result.track.track_number == 4
    assert calls["tag"][1].album == "An Album"


ALBUM_LINK = "https://open.spotify.com/album/" + "a" * 22
PLAYLIST_LINK = "https://open.spotify.com/playlist/" + "p" * 22
TRACK_LINK = "https://open.spotify.com/track/" + "t" * 22


def fake_song_downloader(fail_links=()):
    calls = []

    def download_song(
        link,
        output_dir,
        cookies_from_browser=None,
        album=None,
        track_number=None,
        **options,
    ):
        calls.append((link, album, track_number, cookies_from_browser))
        if link in fail_links:
            raise NoMatchError(f"found no result for {link}")
        track = Track("T", ("A",), 1000, link, album=album, track_number=track_number)
        return Result(track=track, match=GOOD, path=output_dir / "x.mp3")

    return download_song, calls


class FakeProvider:
    name = "fake"

    def __init__(self, track_list=None):
        self.track_list = track_list

    def owns(self, link):
        return True

    def kind_of(self, link):
        return "track" if self.track_list is None else self.track_list.kind

    def fetch_track(self, link):
        return TRACK

    def fetch_list(self, link):
        return self.track_list


def fake_find(track_list=None):
    return lambda link: FakeProvider(track_list)


def test_download_link_downloads_one_track(tmp_path):
    download_song, calls = fake_song_downloader()
    outcomes = download_link(
        TRACK_LINK, tmp_path, find=fake_find(), download_song=download_song
    )
    assert calls == [(TRACK_LINK, None, None, None)]
    assert [o.status for o in outcomes] == ["downloaded"]


def test_download_link_numbers_the_songs_of_an_album(tmp_path):
    download_song, calls = fake_song_downloader()
    album = TrackList("album", "An Album", ("s1", "s2"))
    download_link(
        ALBUM_LINK,
        tmp_path,
        cookies_from_browser="firefox",
        find=fake_find(album),
        download_song=download_song,
    )
    assert calls == [
        ("s1", "An Album", 1, "firefox"),
        ("s2", "An Album", 2, "firefox"),
    ]


def test_download_link_gives_no_album_for_a_playlist(tmp_path):
    download_song, calls = fake_song_downloader()
    playlist = TrackList("playlist", "Mix", ("s1", "s2"))
    download_link(
        PLAYLIST_LINK,
        tmp_path,
        find=fake_find(playlist),
        download_song=download_song,
    )
    assert [(album, number) for _, album, number, _ in calls] == [
        (None, None),
        (None, None),
    ]


def test_download_link_continues_after_a_failed_song(tmp_path):
    download_song, calls = fake_song_downloader(fail_links={"s2"})
    playlist = TrackList("playlist", "Mix", ("s1", "s2", "s3"))
    seen = []
    outcomes = download_link(
        PLAYLIST_LINK,
        tmp_path,
        on_outcome=lambda index, total, outcome: seen.append(
            (index, total, outcome.status)
        ),
        find=fake_find(playlist),
        download_song=download_song,
    )
    assert [o.status for o in outcomes] == ["downloaded", "failed", "downloaded"]
    assert outcomes[1].error == "found no result for s2"
    assert seen == [(1, 3, "downloaded"), (2, 3, "failed"), (3, 3, "downloaded")]


def test_outcome_status_tells_a_skipped_song():
    track = Track("T", ("A",), 1000, "x")
    skipped = Outcome("x", Result(track=track, match=None, path=None, skipped=True))
    assert skipped.status == "skipped"


def test_download_link_gives_the_list_to_the_hook(tmp_path):
    download_song, _ = fake_song_downloader()
    playlist = TrackList("playlist", "Mix", ("s1",))
    seen = []
    download_link(
        PLAYLIST_LINK,
        tmp_path,
        on_list=seen.append,
        find=fake_find(playlist),
        download_song=download_song,
    )
    assert seen == [playlist]


def test_download_track_keeps_the_album_and_number_of_the_provider(tmp_path):
    steps, calls = make_steps([GOOD])
    full = Track(
        title=TRACK.title,
        artists=TRACK.artists,
        duration_ms=TRACK.duration_ms,
        source_url=TRACK.source_url,
        album="Disc Album",
        track_number=2,
    )
    steps["fetch"] = lambda link: full
    result = download_track(
        "link", tmp_path, album="List Name", track_number=14, **steps
    )
    assert result.track.album == "Disc Album"
    assert result.track.track_number == 2


def test_download_track_downloads_a_direct_link_with_no_search(tmp_path):
    steps, calls = make_steps([])
    steps["search"] = lambda track: pytest.fail("a direct link must not search")
    result = download_track("link", tmp_path, direct=True, **steps)
    assert calls["download"][0] == TRACK.source_url
    assert result.match is None
    assert result.skipped is False


def test_download_link_tells_the_song_downloader_about_a_direct_provider(tmp_path):
    seen = []

    class Direct(FakeProvider):
        direct = True

    def download_song(link, output_dir, **options):
        seen.append(options["direct"])
        return Result(track=TRACK, match=None, path=output_dir / "x.mp3")

    download_link(
        "x", tmp_path, find=lambda link: Direct(), download_song=download_song
    )
    download_link(
        "x", tmp_path, find=lambda link: FakeProvider(), download_song=download_song
    )
    assert seen == [True, False]


def test_download_track_leaves_out_a_cover_that_is_not_jpeg_or_png(tmp_path):
    steps, calls = make_steps([GOOD], cover=b"RIFF....WEBPVP8 ")
    download_track("link", tmp_path, **steps)
    assert calls["tag"][2] is None


def test_download_track_uses_the_codec(tmp_path):
    steps, calls = make_steps([GOOD])
    result = download_track("link", tmp_path, codec="flac", **steps)
    assert calls["codec"] == "flac"
    assert result.path.suffix == ".flac"


def test_download_track_skips_only_a_file_of_the_same_format(tmp_path):
    (tmp_path / "First - Song_ Part 1_2.mp3").write_bytes(b"old")
    steps, calls = make_steps([GOOD])
    result = download_track("link", tmp_path, codec="opus", **steps)
    assert result.skipped is False
    assert calls["codec"] == "opus"


def test_download_link_passes_the_codec(tmp_path):
    seen = []

    def download_song(link, output_dir, **options):
        seen.append(options["codec"])
        return Result(track=TRACK, match=None, path=output_dir / "x.m4a")

    download_link(
        "x", tmp_path, codec="m4a", find=fake_find(), download_song=download_song
    )
    assert seen == ["m4a"]


def test_download_track_fills_the_track_before_the_search(tmp_path):
    steps, calls = make_steps([GOOD])
    searched = []
    steps["fill"] = lambda track: dataclasses.replace(track, isrc="FILLED")
    steps["search"] = lambda track: searched.append(track.isrc) or [GOOD]
    result = download_track("link", tmp_path, **steps)
    assert searched == ["FILLED"]
    assert calls["tag"][1].isrc == "FILLED"
    assert result.track.isrc == "FILLED"


def test_download_track_does_not_fill_a_direct_track(tmp_path):
    steps, _ = make_steps([])
    steps["fill"] = lambda track: pytest.fail("a direct track must not be filled")
    download_track("link", tmp_path, direct=True, **steps)


def test_download_track_adds_lyrics_only_when_asked(tmp_path):
    steps, calls = make_steps([GOOD])
    steps["find_lyrics"] = lambda track: "made-up text"
    download_track("link", tmp_path, **steps)
    assert calls["lyrics"] is None
    download_track("link", tmp_path / "again", lyrics=True, **steps)
    assert calls["lyrics"] == "made-up text"


def test_download_track_keeps_going_when_the_lyrics_fail(tmp_path):
    steps, calls = make_steps([GOOD])

    def find_lyrics(track):
        raise OSError("offline")

    steps["find_lyrics"] = find_lyrics
    result = download_track("link", tmp_path, lyrics=True, **steps)
    assert calls["lyrics"] is None
    assert result.skipped is False


def test_download_link_passes_the_lyrics_option(tmp_path):
    seen = []

    def download_song(link, output_dir, **options):
        seen.append(options["lyrics"])
        return Result(track=TRACK, match=None, path=output_dir / "x.mp3")

    download_link(
        "x", tmp_path, lyrics=True, find=fake_find(), download_song=download_song
    )
    assert seen == [True]


def test_download_track_turns_the_yt_dlp_status_into_a_fraction(tmp_path):
    steps, calls = make_steps([GOOD])
    seen = []
    download_track("link", tmp_path, progress=seen.append, **steps)
    hook = calls["progress_hook"]
    hook({"status": "downloading", "downloaded_bytes": 25, "total_bytes": 100})
    hook({"status": "downloading", "downloaded_bytes": 60, "total_bytes_estimate": 120})
    hook({"status": "downloading", "downloaded_bytes": 5})
    hook({"status": "finished"})
    assert seen == [0.25, 0.5, 1.0]


def test_download_track_gives_no_hook_without_progress(tmp_path):
    steps, calls = make_steps([GOOD])
    download_track("link", tmp_path, **steps)
    assert calls["progress_hook"] is None


def test_download_link_reports_the_start_and_the_progress_of_each_song(tmp_path):
    events = []

    def download_song(link, output_dir, **options):
        options["progress"](0.5)
        return Result(track=TRACK, match=None, path=output_dir / "x.mp3")

    playlist = TrackList("playlist", "Mix", ("s1", "s2"))
    download_link(
        PLAYLIST_LINK,
        tmp_path,
        on_start=lambda index, total, link: events.append(
            ("start", index, total, link)
        ),
        on_progress=lambda index, fraction: events.append(
            ("progress", index, fraction)
        ),
        find=fake_find(playlist),
        download_song=download_song,
    )
    assert events == [
        ("start", 1, 2, "s1"),
        ("progress", 1, 0.5),
        ("start", 2, 2, "s2"),
        ("progress", 2, 0.5),
    ]


def test_download_track_uses_the_file_name_template(tmp_path):
    steps, calls = make_steps([GOOD])
    result = download_track("link", tmp_path, template="{artist}/{title}", **steps)
    assert calls["download"][1] == tmp_path / "First" / "Song_ Part 1_2"
    assert result.path == tmp_path / "First" / "Song_ Part 1_2.mp3"


def test_download_link_passes_the_template(tmp_path):
    seen = []

    def download_song(link, output_dir, **options):
        seen.append(options["template"])
        return Result(track=TRACK, match=None, path=output_dir / "x.mp3")

    download_link(
        "x", tmp_path, template="{title}", find=fake_find(), download_song=download_song
    )
    assert seen == ["{title}"]
