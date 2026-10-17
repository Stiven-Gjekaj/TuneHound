"""The main Textual app of TuneHound."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Input, Static


class TuneHoundApp(App[None]):
    """Show the main screen of TuneHound."""

    TITLE = "TuneHound"
    CSS_PATH = "app.tcss"
    AUTO_FOCUS = "#link"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        # The header is a small text wordmark. The two halves take the two
        # end colours of the banner gradient.
        with Horizontal(id="header"):
            yield Static(
                "[b #22d3ee]Tune[/][b #f472b6]Hound[/]", id="wordmark", markup=True
            )
            yield Static("Finds a song and downloads it", id="tagline")
        yield Input(
            placeholder="Paste a link or type a search, then press Enter",
            id="link",
        )
        yield Footer()
