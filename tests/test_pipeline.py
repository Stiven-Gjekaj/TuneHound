from pathlib import Path

import pytest

from tunehound.matching import Candidate
from tunehound.pipeline import (
    NoMatchError,
    Outcome,
    Result,
    download_link,
    download_track,
    safe_filename,
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


def make_steps(candidates, cover=b"\xff\xd8\xffcover", cover_error=None):
    calls = {}

    def fetch(link):
        calls["link"] = link
        return TRACK

    def search(track):
        return candidates

    def download(url, stem, cookies_from_browser=None):
        calls["download"] = (url, stem, cookies_from_browser)
        return stem.with_name(stem.name + ".mp3")

    def get_bytes(url):
        calls["cover_url"] = url
        if cover_error:
            raise cover_error
        return cover

    def tag(path, track, cover_data):
        calls["tag"] = (path, track, cover_data)

    steps = {
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
        fetch=None,
        direct=False,
        album=None,
        track_number=None,
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
