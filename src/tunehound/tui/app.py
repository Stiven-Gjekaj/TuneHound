"""The main Textual app of TuneHound."""

from pathlib import Path
from urllib.parse import urlparse

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Footer, Input, Static


class DownloadRequested(Message):
    """The user asks for a download of one link or one search."""

    def __init__(self, link: str) -> None:
        super().__init__()
        self.link = link


def source_of(text: str) -> str:
    """Return the host of a link, or "search" for plain text."""
    host = urlparse(text).hostname
    if host is None:
        return "search"
    return host.removeprefix("www.").removeprefix("open.")


class TuneHoundApp(App[None]):
    """Show the main screen of TuneHound."""

    TITLE = "TuneHound"
    # A subclass in another file must still find the stylesheet.
    CSS_PATH = Path(__file__).with_name("app.tcss")
    AUTO_FOCUS = "#link"
    # The Input takes the printable keys while it has the focus. Escape
    # moves the focus to the queue, where q closes the app.
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "focus_queue", "Queue"),
        Binding("slash", "focus_link", "Link"),
    ]

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
        # The empty state lies on a layer above the table. It shows until
        # the first row is in the queue.
        with Vertical(id="queue-area"):
            yield DataTable(id="queue", cursor_type="row", zebra_stripes=True)
            yield Static(
                "The queue is empty.\n"
                "Paste a Spotify link or type a search above, then press Enter.",
                id="empty",
            )
        # The status line tells how many items wait in the queue.
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#queue", DataTable)
        table.add_columns("Title", "Artist", "Source", "Status")
        self.update_status()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        link = event.value.strip()
        if not link:
            return
        event.input.clear()
        self.add_to_queue(link)
        self.post_message(DownloadRequested(link))

    def add_to_queue(self, link: str) -> None:
        """Put one link in the queue with the status "waiting"."""
        table = self.query_one("#queue", DataTable)
        # The title and the artist are not known yet. The download code
        # fills them in later. The link itself stands in for the title.
        table.add_row(link, "", source_of(link), "waiting", key=link)
        self.query_one("#empty", Static).display = False
        self.update_status()

    def action_focus_queue(self) -> None:
        """Move the focus to the queue table."""
        self.query_one("#queue", DataTable).focus()

    def action_focus_link(self) -> None:
        """Move the focus to the link input."""
        self.query_one("#link", Input).focus()

    def update_status(self) -> None:
        """Write the count of the queue to the status line."""
        count = self.query_one("#queue", DataTable).row_count
        if count == 0:
            text = "Ready. The queue is empty."
        elif count == 1:
            text = "1 item in the queue, 1 waiting."
        else:
            text = f"{count} items in the queue, {count} waiting."
        self.query_one("#status", Static).update(text)
