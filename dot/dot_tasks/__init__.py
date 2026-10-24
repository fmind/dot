"""Repository-only validation and release commands."""

from pathlib import Path

# The checkout root: every task resolves repository paths from here, whatever its working directory.
ROOT = Path(__file__).resolve().parents[2]
