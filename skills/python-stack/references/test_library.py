from importlib.metadata import version

import <package>


def test_version_matches_metadata() -> None:
    assert <package>.__version__ == version("<slug>")
