import subprocess
import sys

import pytest

from tunehound import __version__
from tunehound.cli import main, summarize


def test_version_flag_prints_the_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"tunehound {__version__}"


def test_no_command_prints_the_help(capsys):
    assert main([]) == 0
    assert capsys.readouterr().out.startswith("usage: tunehound")


def test_unknown_command_fails(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["nosuchcommand"])
    assert exit_info.value.code == 2


def test_module_runs_as_a_program():
    result = subprocess.run(
        [sys.executable, "-m", "tunehound", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == f"tunehound {__version__}"


def make_outcomes(statuses):
    from pathlib import Path

    from tunehound.pipeline import Outcome, Result
    from tunehound.track import Track

    outcomes = []
    for number, status in enumerate(statuses, start=1):
        link = f"link{number}"
        if status == "failed":
            outcomes.append(Outcome(link, error="found nothing"))
            continue
        track = Track(f"Song {number}", ("Artist",), 1000, link)
        result = Result(track, None, Path(f"{number}.mp3"), skipped=status == "skipped")
        outcomes.append(Outcome(link, result))
    return outcomes


def fake_download_link(monkeypatch, statuses, asked=None):
    from tunehound import pipeline

    def download_link(link, output, cookies_from_browser=None, on_outcome=None):
        if asked is not None:
            asked.update(link=link, output=output, browser=cookies_from_browser)
        outcomes = make_outcomes(statuses)
        for index, outcome in enumerate(outcomes, start=1):
            on_outcome(index, len(outcomes), outcome)
        return outcomes

    monkeypatch.setattr(pipeline, "download_link", download_link)


def test_download_command_passes_the_options(monkeypatch, tmp_path):
    from pathlib import Path

    asked = {}
    fake_download_link(monkeypatch, ["downloaded"], asked)
    code = main(
        [
            "download",
            "spotify:album:x",
            "-o",
            str(tmp_path),
            "--cookies-from-browser",
            "firefox",
        ]
    )
    assert code == 0
    assert asked == {
        "link": "spotify:album:x",
        "output": Path(tmp_path),
        "browser": "firefox",
    }


def test_download_command_prints_each_song_and_a_summary(monkeypatch, capsys):
    fake_download_link(monkeypatch, ["downloaded", "skipped", "failed"])
    assert main(["download", "spotify:album:x"]) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "[1/3] downloaded Artist - Song 1",
        "[2/3] skipped    Artist - Song 2",
        "3 songs: 1 downloaded, 1 skipped, 1 failed.",
    ]
    assert captured.err == "[3/3] failed     link3: found nothing\n"


def test_download_command_succeeds_when_no_song_fails(monkeypatch, capsys):
    fake_download_link(monkeypatch, ["downloaded", "skipped"])
    assert main(["download", "spotify:album:x"]) == 0


def test_summarize_says_song_for_one_song():
    assert summarize(make_outcomes(["downloaded"])) == (
        "1 song: 1 downloaded, 0 skipped, 0 failed."
    )


def test_download_command_refuses_a_bad_link(capsys):
    assert main(["download", "https://example.com/not-spotify"]) == 1
    assert "not a Spotify link" in capsys.readouterr().err
