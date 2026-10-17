from textual.widgets import Static

from tunehound import cli
from tunehound.tui import TuneHoundApp


async def test_app_shows_the_welcome_text():
    app = TuneHoundApp()
    async with app.run_test():
        welcome = app.query_one("#welcome", Static)
        assert "Paste a link" in str(welcome.render())


async def test_q_key_closes_the_app():
    app = TuneHoundApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


def test_tui_command_opens_the_app(monkeypatch):
    opened = []
    monkeypatch.setattr(TuneHoundApp, "run", lambda self: opened.append(self))
    assert cli.main(["tui"]) == 0
    assert len(opened) == 1
