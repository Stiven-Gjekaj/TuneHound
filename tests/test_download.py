import pytest
import yt_dlp

from tunehound.download import DownloadError, build_options, download_audio


class FakeDownloader:
    def __init__(self, options, make_file=True, fail=False):
        self.options = options
        self.make_file = make_file
        self.fail = fail
        self.urls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def download(self, urls):
        self.urls.extend(urls)
        if self.fail:
            raise yt_dlp.utils.DownloadError("no audio")
        if self.make_file:
            codec = self.options["postprocessors"][0]["preferredcodec"]
            stem = self.options["outtmpl"].removesuffix(".%(ext)s")
            with open(f"{stem}.{codec}", "wb") as file:
                file.write(b"audio")


def test_build_options_extract_the_audio_to_the_codec(tmp_path):
    options = build_options(tmp_path / "Artist - Song", codec="opus")
    assert options["outtmpl"] == f"{tmp_path / 'Artist - Song'}.%(ext)s"
    assert options["format"] == "bestaudio/best"
    assert options["noplaylist"] is True
    [processor] = options["postprocessors"]
    assert processor["key"] == "FFmpegExtractAudio"
    assert processor["preferredcodec"] == "opus"


def test_build_options_add_the_progress_hook(tmp_path):
    def hook(status):
        return None

    assert build_options(tmp_path / "x", progress_hook=hook)["progress_hooks"] == [hook]
    assert "progress_hooks" not in build_options(tmp_path / "x")


def test_download_audio_returns_the_audio_file(tmp_path):
    made = []

    def factory(options):
        made.append(FakeDownloader(options))
        return made[-1]

    stem = tmp_path / "new folder" / "Artist - Song. Part 1"
    path = download_audio(
        "https://www.youtube.com/watch?v=x", stem, downloader_factory=factory
    )
    assert path == tmp_path / "new folder" / "Artist - Song. Part 1.mp3"
    assert path.read_bytes() == b"audio"
    assert made[0].urls == ["https://www.youtube.com/watch?v=x"]


def test_download_audio_fails_when_no_file_comes(tmp_path):
    def factory(options):
        return FakeDownloader(options, make_file=False)

    with pytest.raises(DownloadError):
        download_audio("https://x.invalid", tmp_path / "a", downloader_factory=factory)


def test_download_audio_turns_a_yt_dlp_error_into_a_download_error(tmp_path):
    def factory(options):
        return FakeDownloader(options, fail=True)

    with pytest.raises(DownloadError, match="no audio"):
        download_audio("https://x.invalid", tmp_path / "a", downloader_factory=factory)


def test_build_options_read_the_cookies_of_a_browser(tmp_path):
    options = build_options(tmp_path / "x", cookies_from_browser="firefox")
    assert options["cookiesfrombrowser"] == ("firefox",)
    assert "cookiesfrombrowser" not in build_options(tmp_path / "x")


def test_download_audio_passes_the_browser_to_yt_dlp(tmp_path):
    made = []

    def factory(options):
        made.append(FakeDownloader(options))
        return made[-1]

    download_audio(
        "https://x.invalid",
        tmp_path / "a",
        cookies_from_browser="chrome",
        downloader_factory=factory,
    )
    assert made[0].options["cookiesfrombrowser"] == ("chrome",)
