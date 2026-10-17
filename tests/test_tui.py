from textual.widgets import DataTable, Input, Static

from tunehound import cli
from tunehound.tui import DownloadRequested, TuneHoundApp
from tunehound.tui.app import source_of

LINK = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"


class RecordingApp(TuneHoundApp):
    """Keep each DownloadRequested message that the app posts."""

    def __init__(self) -> None:
        # The fake download does nothing, so the row stays "waiting" and
        # the test does not touch the network.
        super().__init__(download_link=lambda link, output, **options: [])
        self.requests: list[str] = []

    def on_download_requested(self, message: DownloadRequested) -> None:
        self.requests.append(message.link)


def rows_of(app: TuneHoundApp) -> list[list[str]]:
    table = app.query_one("#queue", DataTable)
    return [
        [str(cell) for cell in table.get_row_at(index)]
        for index in range(table.row_count)
    ]


async def test_app_shows_the_wordmark_and_the_link_input():
    app = TuneHoundApp()
    async with app.run_test():
        wordmark = app.query_one("#wordmark", Static)
        assert "TuneHound" in str(wordmark.render())
        link = app.query_one("#link", Input)
        assert link.has_focus
        assert "Paste a link" in link.placeholder


async def test_queue_starts_empty_with_the_empty_state():
    app = TuneHoundApp()
    async with app.run_test():
        table = app.query_one("#queue", DataTable)
        assert [str(c.label) for c in table.columns.values()] == [
            "Title",
            "Artist",
            "Source",
            "Status",
        ]
        assert table.row_count == 0
        empty = app.query_one("#empty", Static)
        assert empty.display
        assert "queue is empty" in str(empty.render())
        assert "empty" in str(app.query_one("#status", Static).render())


async def test_submit_posts_the_message_and_adds_a_waiting_row():
    app = RecordingApp()
    async with app.run_test() as pilot:
        await pilot.press(*LINK)
        await pilot.press("enter")
        await pilot.pause()
        assert app.requests == [LINK]
        assert rows_of(app) == [[LINK, "", "spotify.com", "waiting"]]
        assert not app.query_one("#empty", Static).display
        assert app.query_one("#link", Input).value == ""
        status = str(app.query_one("#status", Static).render())
        assert status == "1 item: 1 waiting, 0 active, 0 done, 0 failed."


async def test_empty_submit_adds_nothing():
    app = RecordingApp()
    async with app.run_test() as pilot:
        await pilot.press("space", "enter")
        await pilot.pause()
        assert app.requests == []
        assert rows_of(app) == []
        assert app.query_one("#empty", Static).display


def test_source_of_a_search_is_search():
    assert source_of("daft punk around the world") == "search"
    assert source_of("https://www.youtube.com/watch?v=abc") == "youtube.com"


async def test_escape_moves_the_focus_to_the_queue_and_slash_back():
    app = TuneHoundApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert app.query_one("#queue", DataTable).has_focus
        await pilot.press("slash")
        assert app.query_one("#link", Input).has_focus


async def test_q_key_closes_the_app():
    app = TuneHoundApp()
    async with app.run_test() as pilot:
        await pilot.press("escape", "q")
        await pilot.pause()
        assert not app.is_running


def test_tui_command_opens_the_app(monkeypatch):
    opened = []
    monkeypatch.setattr(TuneHoundApp, "run", lambda self: opened.append(self))
    assert cli.main(["tui"]) == 0
    assert len(opened) == 1


def fake_result(title, artist="Artist", skipped=False):
    from pathlib import Path

    from tunehound.pipeline import Result
    from tunehound.track import Track

    track = Track(title, (artist,), 1000, "x")
    return Result(track, None, Path(f"{title}.mp3"), skipped=skipped)


def song_download(link, output, **hooks):
    from tunehound.pipeline import Outcome

    hooks["on_start"](1, 1, link)
    hooks["on_progress"](1, 0.42)
    outcome = Outcome(link, fake_result("A Song"))
    hooks["on_outcome"](1, 1, outcome)
    return [outcome]


def list_download(link, output, **hooks):
    from tunehound.pipeline import Outcome
    from tunehound.providers import TrackList

    hooks["on_list"](TrackList("album", "An Album", ("s1", "s2")))
    outcomes = []
    for index, outcome in enumerate(
        [
            Outcome("s1", fake_result("One", skipped=True)),
            Outcome("s2", error="no match"),
        ],
        start=1,
    ):
        hooks["on_start"](index, 2, outcome.link)
        hooks["on_outcome"](index, 2, outcome)
        outcomes.append(outcome)
    return outcomes


async def submit(app, pilot, text):
    app.query_one("#link", Input).value = text
    await pilot.press("enter")
    await app.workers.wait_for_complete()
    await pilot.pause()


async def test_a_song_download_fills_the_row():
    app = TuneHoundApp(download_link=song_download)
    async with app.run_test() as pilot:
        await submit(app, pilot, LINK)
        assert rows_of(app) == [["A Song", "Artist", "spotify.com", "downloaded"]]
        status = str(app.query_one("#status", Static).render())
        assert status == "1 item: 0 waiting, 0 active, 1 done, 0 failed."


async def test_a_list_download_adds_a_row_for_each_song():
    app = TuneHoundApp(download_link=list_download)
    async with app.run_test() as pilot:
        await submit(app, pilot, "https://www.deezer.com/album/7")
        assert rows_of(app) == [
            ["An Album", "", "deezer.com", "downloaded"],
            ["  One", "Artist", "search", "skipped"],
            ["  s2", "", "search", "failed"],
        ]
        status = str(app.query_one("#status", Static).render())
        assert status.startswith("3 items: 0 waiting, 0 active, 2 done, 1 failed.")
        assert status.endswith("Last error: no match")


async def test_a_provider_error_marks_the_row_failed():
    from tunehound.providers import ProviderError

    def broken(link, output, **hooks):
        raise ProviderError("TuneHound does not know this link: x")

    app = TuneHoundApp(download_link=broken)
    async with app.run_test() as pilot:
        await submit(app, pilot, "https://example.com/x")
        assert rows_of(app)[0][3] == "failed"
        assert "does not know this link" in str(
            app.query_one("#status", Static).render()
        )


async def test_the_app_passes_its_options_to_the_download(tmp_path):
    asked = {}

    def recording(link, output, **options):
        asked.update(options, output=output)
        return []

    app = TuneHoundApp(
        output_dir=tmp_path,
        codec="flac",
        lyrics=True,
        cookies_from_browser="firefox",
        download_link=recording,
    )
    async with app.run_test() as pilot:
        await submit(app, pilot, LINK)
    assert asked["output"] == tmp_path
    assert (asked["codec"], asked["lyrics"]) == ("flac", True)
    assert asked["cookies_from_browser"] == "firefox"


def test_state_of_groups_the_statuses():
    from tunehound.tui.app import state_of

    assert [state_of(s) for s in ("waiting", "searching", "42%", "3/10")] == [
        "waiting",
        "active",
        "active",
        "active",
    ]
    assert [state_of(s) for s in ("downloaded", "skipped", "failed")] == [
        "done",
        "done",
        "failed",
    ]
