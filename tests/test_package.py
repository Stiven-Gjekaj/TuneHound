import re

import tunehound


def test_version_has_three_parts():
    assert re.fullmatch(r"\d+\.\d+\.\d+", tunehound.__version__)
