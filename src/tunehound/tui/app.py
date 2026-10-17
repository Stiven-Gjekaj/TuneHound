"""The main Textual app of TuneHound."""

import threading
from collections.abc import Callable
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from textual.message import Message
from textual.widgets import DataTable, Footer, Input, Static

from tunehound import pipeline
from tunehound.download import DEFAULT_CODEC
from tunehound.providers import ProviderError

MAX_PARALLEL = 3
# The widths of the narrow columns. The title column takes the rest.
FIXED_WIDTHS = {"artist": 24, "source": 22, "status": 12}
MIN_TITLE_WIDTH = 20
DONE_STATES = ("downloaded", "skipped")


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


def state_of(status: str) -> str:
    """Return the group of a status: waiting, active, done, or failed."""
    if status == "waiting":
        return "waiting"
    if status in DONE_STATES:
        return "done"
    if status == "failed":
        return "failed"
    return "active"


class TuneHoundApp(App[None]):
    """Show the main screen of TuneHound, and run the downloads."""

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

    def __init__(
        self,
        output_dir: Path | None = None,
        codec: str = DEFAULT_CODEC,
        lyrics: bool = False,
        cookies_from_browser: str | None = None,
        download_link: Callable[..., list] | None = None,
        max_parallel: int = MAX_PARALLEL,
    ) -> None:
        super().__init__()
        self.output_dir = output_dir or Path.cwd()
        self.codec = codec
        self.lyrics = lyrics
        self.cookies_from_browser = cookies_from_browser
        self._download_link = download_link or pipeline.download_link
        self._slots = threading.Semaphore(max_parallel)
        self._count = 0
        self._states: dict[str, str] = {}
        self._last_error = ""

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
        for label in ("Title", "Artist", "Source", "Status"):
            table.add_column(label, key=label.lower())
        # The table has its real width only after the first layout.
        self.call_after_refresh(self.fit_columns)
        self.update_status()

    def on_resize(self) -> None:
        self.call_after_refresh(self.fit_columns)

    def fit_columns(self) -> None:
        """Give each column a fixed width, so that a long link cannot push
        the status out of the screen."""
        table = self.query_one("#queue", DataTable)
        width = table.size.width or self.size.width
        padding = 2 * table.cell_padding * len(table.columns)
        title = max(MIN_TITLE_WIDTH, width - sum(FIXED_WIDTHS.values()) - padding)
        for key, column in table.columns.items():
            column.auto_width = False
            column.width = FIXED_WIDTHS.get(key.value, title)
        # Rows that came before this fit keep the old scroll width, so set
        # the width again from the new columns.
        total = sum(column.get_render_width(table) for column in table.columns.values())
        table.virtual_size = Size(total, table.virtual_size.height)
        table.refresh()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        link = event.value.strip()
        if not link:
            return
        event.input.clear()
        self.add_to_queue(link)
        self.post_message(DownloadRequested(link))

    def add_to_queue(self, link: str) -> str:
        """Put one link in the queue with the status "waiting".

        Return the key of the new row.
        """
        self._count += 1
        key = f"item-{self._count}"
        table = self.query_one("#queue", DataTable)
        # The title and the artist are not known yet. The download fills
        # them in later. The link itself stands in for the title.
        table.add_row(link, "", source_of(link), "waiting", key=key)
        self._states[key] = "waiting"
        self.query_one("#empty", Static).display = False
        self.update_status()
        return key

    def on_download_requested(self, message: DownloadRequested) -> None:
        key = f"item-{self._count}"
        self.run_worker(
            partial(self._run_download, key, message.link),
            thread=True,
            group="downloads",
            exit_on_error=False,
        )

    def _run_download(self, key: str, link: str) -> None:
        """Download a link in a worker thread, and report to the screen."""
        job = {"is_list": False, "total": 0, "done": 0}

        def on_list(track_list) -> None:
            job["is_list"] = True
            job["total"] = len(track_list.track_links)
            name = track_list.name or link
            self.call_from_thread(self.set_row, key, name, None, f"0/{job['total']}")

        def row_key(index: int) -> str:
            return f"{key}-{index}" if job["is_list"] else key

        def on_start(index: int, total: int, song_link: str) -> None:
            if job["is_list"]:
                self.call_from_thread(self.add_child, key, index, song_link)
            else:
                self.call_from_thread(self.set_row, key, None, None, "searching")

        def on_progress(index: int, fraction: float) -> None:
            status = f"{round(fraction * 100)}%"
            self.call_from_thread(self.set_row, row_key(index), None, None, status)

        def on_outcome(index: int, total: int, outcome) -> None:
            title = artist = None
            if outcome.result is not None:
                title = outcome.result.track.title
                artist = outcome.result.track.artist
            else:
                self.call_from_thread(self.note_error, outcome.error or "")
            if job["is_list"]:
                title = f"  {title}" if title else None
            self.call_from_thread(
                self.set_row, row_key(index), title, artist, outcome.status
            )
            if job["is_list"]:
                job["done"] += 1
                status = f"{job['done']}/{job['total']}"
                if job["done"] == job["total"]:
                    status = "downloaded"
                self.call_from_thread(self.set_row, key, None, None, status)

        with self._slots:
            try:
                outcomes = self._download_link(
                    link,
                    self.output_dir,
                    cookies_from_browser=self.cookies_from_browser,
                    codec=self.codec,
                    lyrics=self.lyrics,
                    on_outcome=on_outcome,
                    on_list=on_list,
                    on_start=on_start,
                    on_progress=on_progress,
                )
            except (ProviderError, OSError) as error:
                self.call_from_thread(self.note_error, str(error))
                self.call_from_thread(self.set_row, key, None, None, "failed")
                return
        if job["is_list"] and not outcomes:
            self.call_from_thread(self.set_row, key, None, None, "downloaded")

    def add_child(self, parent: str, index: int, song_link: str) -> None:
        """Add a row for one song of a list, under the rows of the list."""
        table = self.query_one("#queue", DataTable)
        key = f"{parent}-{index}"
        table.add_row(f"  {song_link}", "", source_of(song_link), "searching", key=key)
        self._states[key] = "active"
        self.update_status()

    def set_row(
        self, key: str, title: str | None, artist: str | None, status: str
    ) -> None:
        """Change the cells of a row. A None value keeps the cell."""
        table = self.query_one("#queue", DataTable)
        if title is not None:
            table.update_cell(key, "title", title)
        if artist is not None:
            table.update_cell(key, "artist", artist)
        table.update_cell(key, "status", status)
        self._states[key] = state_of(status)
        self.update_status()

    def note_error(self, message: str) -> None:
        """Keep the last error, to show it in the status line."""
        self._last_error = message
        self.update_status()

    def action_focus_queue(self) -> None:
        """Move the focus to the queue table."""
        self.query_one("#queue", DataTable).focus()

    def action_focus_link(self) -> None:
        """Move the focus to the link input."""
        self.query_one("#link", Input).focus()

    def update_status(self) -> None:
        """Write the count of each state to the status line."""
        count = len(self._states)
        if count == 0:
            text = "Ready. The queue is empty."
        else:
            groups = {name: 0 for name in ("waiting", "active", "done", "failed")}
            for state in self._states.values():
                groups[state] += 1
            items = "item" if count == 1 else "items"
            parts = ", ".join(f"{number} {name}" for name, number in groups.items())
            text = f"{count} {items}: {parts}."
            if self._last_error:
                text += f" Last error: {self._last_error}"
        self.query_one("#status", Static).update(text)
