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
