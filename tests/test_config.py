from pathlib import Path

import pytest

from tunehound.config import ConfigError, default_path, load, shown, spotify_keys


def write(tmp_path, text):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_reads_every_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = write(
        tmp_path,
        'output = "~/Music"\n'
        'format = "flac"\n'
        "lyrics = true\n"
        'template = "{artist}/{title}"\n'
        'cookies_from_browser = "firefox"\n',
    )
    assert load(path) == {
        "output": tmp_path / "Music",
        "format": "flac",
        "lyrics": True,
        "template": "{artist}/{title}",
        "cookies_from_browser": "firefox",
    }


def test_load_gives_nothing_for_a_missing_file(tmp_path):
    assert load(tmp_path / "none.toml") == {}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('colour = "red"\n', "unknown key"),
        ('format = "wav"\n', "format must be"),
        ('lyrics = "yes"\n', "lyrics must be"),
        ('template = "{genre}"\n', "unknown field"),
        ("output = 5\n", "output must be"),
        ('cookies_from_browser = ""\n', "cookies_from_browser must be"),
        ("format = \n", "cannot read"),
    ],
)
def test_load_refuses_a_bad_file(tmp_path, text, message):
    with pytest.raises(ConfigError, match=message):
        load(write(tmp_path, text))


def test_default_path_uses_the_environment_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("TUNEHOUND_CONFIG", str(tmp_path / "my.toml"))
    assert default_path() == tmp_path / "my.toml"


def test_default_path_uses_the_xdg_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("TUNEHOUND_CONFIG", raising=False)
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_path() == tmp_path / "tunehound" / "config.toml"


def test_default_path_falls_back_to_the_home_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("TUNEHOUND_CONFIG", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_path() == tmp_path / ".config" / "tunehound" / "config.toml"


def test_default_path_uses_appdata_on_windows(monkeypatch, tmp_path):
    monkeypatch.delenv("TUNEHOUND_CONFIG", raising=False)
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_path() == Path(tmp_path) / "tunehound" / "config.toml"


@pytest.fixture
def no_spotify_environment(monkeypatch):
    monkeypatch.delenv("TUNEHOUND_SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("TUNEHOUND_SPOTIFY_CLIENT_SECRET", raising=False)


def test_load_reads_the_spotify_keys(tmp_path):
    path = write(
        tmp_path, 'spotify_client_id = " abc "\nspotify_client_secret = "xyz"\n'
    )
    assert load(path) == {"spotify_client_id": "abc", "spotify_client_secret": "xyz"}


def test_spotify_keys_come_from_the_file(no_spotify_environment):
    values = {"spotify_client_id": "abc", "spotify_client_secret": "xyz"}
    assert spotify_keys(values) == ("abc", "xyz")


def test_spotify_keys_from_the_environment_win(monkeypatch):
    monkeypatch.setenv("TUNEHOUND_SPOTIFY_CLIENT_ID", "env-id")
    monkeypatch.setenv("TUNEHOUND_SPOTIFY_CLIENT_SECRET", "env-secret")
    values = {"spotify_client_id": "abc", "spotify_client_secret": "xyz"}
    assert spotify_keys(values) == ("env-id", "env-secret")


def test_spotify_keys_are_none_when_there_are_none(no_spotify_environment):
    assert spotify_keys({}) is None


def test_spotify_keys_need_both_keys(no_spotify_environment):
    with pytest.raises(ConfigError, match="give both"):
        spotify_keys({"spotify_client_id": "abc"})


def test_shown_hides_the_secret():
    assert shown("spotify_client_secret", "xyz") == "(hidden)"
    assert shown("spotify_client_id", "abc") == "abc"
