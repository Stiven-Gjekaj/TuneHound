import subprocess
import sys

import pytest

from tunehound import __version__
from tunehound.cli import main


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


def test_download_command_prints_the_result(monkeypatch, capsys, tmp_path):
    from pathlib import Path

    from tunehound import pipeline
    from tunehound.matching import Candidate
    from tunehound.track import Track

    asked = {}

    def fake_download_track(link, output, cookies_from_browser=None):
        asked.update(link=link, output=output, browser=cookies_from_browser)
        track = Track("Song", ("Artist",), 1000, "https://x.invalid")
        match = Candidate("abc", "Song", "Artist - Topic", 1.0, "youtube")
        return pipeline.Result(track, match, output / "Artist - Song.mp3")

    monkeypatch.setattr(pipeline, "download_track", fake_download_track)
    code = main(
        [
            "download",
            "spotify:track:x",
            "-o",
            str(tmp_path),
            "--cookies-from-browser",
            "firefox",
        ]
    )
    assert code == 0
    assert asked == {
        "link": "spotify:track:x",
        "output": Path(tmp_path),
        "browser": "firefox",
    }
    out = capsys.readouterr().out
    assert "Artist - Song" in out
    assert "https://www.youtube.com/watch?v=abc" in out
    assert str(tmp_path / "Artist - Song.mp3") in out


def test_download_command_reports_an_error(monkeypatch, capsys):
    from tunehound import pipeline

    def fake_download_track(link, output, cookies_from_browser=None):
        raise pipeline.NoMatchError("found no result for Artist - Song")

    monkeypatch.setattr(pipeline, "download_track", fake_download_track)
    assert main(["download", "spotify:track:x"]) == 1
    assert capsys.readouterr().err == "tunehound: found no result for Artist - Song\n"


def test_download_command_refuses_a_bad_link(capsys):
    assert main(["download", "https://example.com/not-spotify"]) == 1
    assert "not a Spotify link" in capsys.readouterr().err
