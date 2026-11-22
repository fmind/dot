"""Python implementation of the dot CLI."""

from importlib.metadata import version

__all__ = ["__version__"]


def __getattr__(name: str) -> str:
    if name == "__version__":
        value = version("fmind-dot")
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
