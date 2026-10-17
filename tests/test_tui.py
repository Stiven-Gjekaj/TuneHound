from textual.widgets import DataTable, Input, Static

from tunehound import cli
from tunehound.tui import DownloadRequested, TuneHoundApp
from tunehound.tui.app import source_of

LINK = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"


class RecordingApp(TuneHoundApp):
    """Keep each DownloadRequested message that the app posts."""

    def __init__(self) -> None:
        super().__init__()
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


async def test_q_key_closes_the_app():
    app = TuneHoundApp()
    async with app.run_test() as pilot:
        app.set_focus(None)
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


def test_tui_command_opens_the_app(monkeypatch):
    opened = []
    monkeypatch.setattr(TuneHoundApp, "run", lambda self: opened.append(self))
    assert cli.main(["tui"]) == 0
    assert len(opened) == 1
