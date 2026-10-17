from textual.widgets import Input, Static

from tunehound import cli
from tunehound.tui import TuneHoundApp


async def test_app_shows_the_wordmark_and_the_link_input():
    app = TuneHoundApp()
    async with app.run_test():
        wordmark = app.query_one("#wordmark", Static)
        assert "TuneHound" in str(wordmark.render())
        link = app.query_one("#link", Input)
        assert link.has_focus
        assert "Paste a link" in link.placeholder


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
