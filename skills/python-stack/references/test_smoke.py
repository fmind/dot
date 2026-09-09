from <package> import __main__ as module_entrypoint
from <package> import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"
    assert module_entrypoint.__name__.endswith(".__main__")
