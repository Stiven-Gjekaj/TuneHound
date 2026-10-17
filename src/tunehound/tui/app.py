"""The main Textual app of TuneHound."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class TuneHoundApp(App[None]):
    """Show the main screen of TuneHound."""

    TITLE = "TuneHound"
    SUB_TITLE = "Download music from many providers"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Paste a link or type a search to start.", id="welcome")
        yield Footer()
