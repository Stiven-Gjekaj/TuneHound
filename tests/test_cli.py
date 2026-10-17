import subprocess
import sys
from pathlib import Path

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

    def download_link(
        link,
        output,
        cookies_from_browser=None,
        codec="mp3",
        lyrics=False,
        template="{artist} - {title}",
        on_outcome=None,
        on_list=None,
    ):
        if asked is not None:
            asked.update(
                link=link,
                output=output,
                browser=cookies_from_browser,
                codec=codec,
                lyrics=lyrics,
                template=template,
            )
        outcomes = make_outcomes(statuses)
        for index, outcome in enumerate(outcomes, start=1):
            on_outcome(index, len(outcomes), outcome)
        return outcomes

    monkeypatch.setattr(pipeline, "download_link", download_link)


def test_download_command_passes_the_options(monkeypatch, tmp_path):

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
        "codec": "mp3",
        "lyrics": False,
        "template": "{artist} - {title}",
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
    assert "does not know this link" in capsys.readouterr().err


def test_download_command_warns_about_a_list_that_can_be_cut(monkeypatch, capsys):
    from tunehound import pipeline
    from tunehound.providers.spotify import TrackList

    def download_link(
        link,
        output,
        cookies_from_browser=None,
        codec="mp3",
        lyrics=False,
        template="{artist} - {title}",
        on_outcome=None,
        on_list=None,
    ):
        on_list(TrackList("playlist", "Mix", tuple(f"s{n}" for n in range(100)), 100))
        return []

    monkeypatch.setattr(pipeline, "download_link", download_link)
    main(["download", "spotify:playlist:x"])
    assert "the list has 100 songs" in capsys.readouterr().err


def test_download_help_names_every_provider(capsys):
    with pytest.raises(SystemExit):
        main(["download", "--help"])
    help_text = " ".join(capsys.readouterr().out.split())
    for name in (
        "Spotify",
        "Deezer",
        "Apple Music",
        "YouTube",
        "SoundCloud",
        "Bandcamp",
    ):
        assert name in help_text
    assert "search text" in help_text


def test_download_command_passes_the_format(monkeypatch):
    asked = {}
    fake_download_link(monkeypatch, [], asked)
    main(["download", "x", "--format", "opus"])
    assert asked["codec"] == "opus"


def test_download_command_refuses_an_unknown_format(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["download", "x", "--format", "wav"])
    assert exit_info.value.code == 2


def test_download_command_passes_the_lyrics_option(monkeypatch):
    asked = {}
    fake_download_link(monkeypatch, [], asked)
    main(["download", "x", "--lyrics"])
    assert asked["lyrics"] is True


def test_download_command_passes_the_template(monkeypatch):
    asked = {}
    fake_download_link(monkeypatch, [], asked)
    main(["download", "x", "--template", "{artist}/{album}/{track_number:02} {title}"])
    assert asked["template"] == "{artist}/{album}/{track_number:02} {title}"


def test_download_command_refuses_a_bad_template(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["download", "x", "--template", "{genre} - {title}"])
    assert exit_info.value.code == 2
    assert "unknown field {genre}" in capsys.readouterr().err


@pytest.fixture(autouse=True)
def no_user_config(monkeypatch, tmp_path_factory):
    """Keep the configuration file of the user out of every test."""
    folder = tmp_path_factory.mktemp("config")
    monkeypatch.setenv("TUNEHOUND_CONFIG", str(folder / "none.toml"))
    monkeypatch.delenv("TUNEHOUND_SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("TUNEHOUND_SPOTIFY_CLIENT_SECRET", raising=False)
    return folder


def test_download_command_takes_its_defaults_from_the_config_file(
    monkeypatch, tmp_path
):
    config = tmp_path / "config.toml"
    config.write_text(
        f'output = "{tmp_path / "Music"}"\n'
        'format = "opus"\n'
        "lyrics = true\n"
        'template = "{title}"\n'
        'cookies_from_browser = "safari"\n'
    )
    asked = {}
    fake_download_link(monkeypatch, [], asked)
    assert main(["--config", str(config), "download", "x"]) == 0
    assert asked == {
        "link": "x",
        "output": tmp_path / "Music",
        "browser": "safari",
        "codec": "opus",
        "lyrics": True,
        "template": "{title}",
    }


def test_the_command_line_wins_over_the_config_file(monkeypatch, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('format = "opus"\nlyrics = true\n')
    monkeypatch.setenv("TUNEHOUND_CONFIG", str(config))
    asked = {}
    fake_download_link(monkeypatch, [], asked)
    main(["download", "x", "--format", "flac", "--no-lyrics"])
    assert (asked["codec"], asked["lyrics"]) == ("flac", False)


def test_a_bad_config_file_stops_the_command(tmp_path, capsys):
    config = tmp_path / "config.toml"
    config.write_text('format = "wav"\n')
    assert main(["--config", str(config), "download", "x"]) == 2
    assert "format must be" in capsys.readouterr().err


def test_a_missing_config_file_given_by_name_stops_the_command(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "none.toml"), "download", "x"]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_config_command_shows_the_path_and_the_values(tmp_path, capsys, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('format = "flac"\n')
    monkeypatch.setenv("TUNEHOUND_CONFIG", str(config))
    assert main(["config"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        f"{config} (found)",
        "  format = flac",
        "Spotify: the embed page, with at most 100 songs of a playlist",
    ]


def test_config_command_says_when_there_is_no_file(capsys, no_user_config):
    assert main(["config"]) == 0
    out = capsys.readouterr().out
    assert "not found" in out
    assert str(no_user_config / "none.toml") in out


def test_spotify_keys_turn_on_the_web_api(monkeypatch, tmp_path, capsys):
    from tunehound import providers
    from tunehound.providers.spotify import SpotifyProvider

    [spotify] = [p for p in providers.PROVIDERS if isinstance(p, SpotifyProvider)]
    monkeypatch.setattr(spotify, "api", None)
    config = tmp_path / "config.toml"
    config.write_text('spotify_client_id = "abc"\nspotify_client_secret = "xyz"\n')
    assert main(["--config", str(config), "config"]) == 0
    out = capsys.readouterr().out
    assert "spotify_client_secret = (hidden)" in out
    assert "xyz" not in out
    assert "Spotify: the Web API" in out
    assert spotify.api is not None


def test_one_spotify_key_alone_stops_the_command(tmp_path, capsys):
    config = tmp_path / "config.toml"
    config.write_text('spotify_client_id = "abc"\n')
    assert main(["--config", str(config), "config"]) == 2
    assert "give both" in capsys.readouterr().err


def test_read_input_skips_empty_lines_and_comments(tmp_path):
    from tunehound.cli import read_input

    path = tmp_path / "links.txt"
    path.write_text(
        "\ufeffhttps://open.spotify.com/track/a\n"
        "\n"
        "  # a comment\n"
        "  artist - title  \r\n",
        encoding="utf-8",
    )
    assert read_input(path) == ["https://open.spotify.com/track/a", "artist - title"]


def test_input_file_downloads_each_line(monkeypatch, tmp_path, capsys):
    from tunehound import pipeline

    path = tmp_path / "links.txt"
    path.write_text("one\nbad\nthree\n")
    asked = []

    def download_link(link, output, **hooks):
        asked.append(link)
        if link == "bad":
            raise pipeline.ProviderError("TuneHound does not know this link: bad")
        [outcome] = make_outcomes(["downloaded"])
        hooks["on_outcome"](1, 1, outcome)
        return [outcome]

    monkeypatch.setattr(pipeline, "download_link", download_link)
    assert main(["download", "--input", str(path)]) == 1
    assert asked == ["one", "bad", "three"]
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "[1/3] downloaded Artist - Song 1",
        "[3/3] downloaded Artist - Song 1",
        "3 songs: 2 downloaded, 0 skipped, 1 failed.",
    ]
    assert (
        captured.err == "[2/3] failed     bad: TuneHound does not know this link: bad\n"
    )


def test_input_file_shows_the_song_of_a_list_line(monkeypatch, tmp_path, capsys):
    from tunehound import pipeline

    path = tmp_path / "links.txt"
    path.write_text("a list\nb\n")

    def download_link(link, output, **hooks):
        outcomes = make_outcomes(
            ["downloaded", "skipped"] if link == "a list" else ["downloaded"]
        )
        for index, outcome in enumerate(outcomes, start=1):
            hooks["on_outcome"](index, len(outcomes), outcome)
        return outcomes

    monkeypatch.setattr(pipeline, "download_link", download_link)
    assert main(["download", "-i", str(path)]) == 0
    assert capsys.readouterr().out.splitlines()[:3] == [
        "[1/2 song 1/2] downloaded Artist - Song 1",
        "[1/2 song 2/2] skipped    Artist - Song 2",
        "[2/2] downloaded Artist - Song 1",
    ]


@pytest.mark.parametrize("argv", [["download"], ["download", "x", "--input", "f.txt"]])
def test_download_needs_one_link_or_one_input_file(argv, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2
    assert "give one LINK or one --input FILE" in capsys.readouterr().err


def test_a_missing_input_file_stops_the_command(tmp_path, capsys):
    assert main(["download", "--input", str(tmp_path / "none.txt")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_an_empty_input_file_stops_the_command(tmp_path, capsys):
    path = tmp_path / "links.txt"
    path.write_text("\n# only a comment\n")
    assert main(["download", "--input", str(path)]) == 2
    assert "has no links" in capsys.readouterr().err
