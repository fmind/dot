"""Readable text reports without wide tables or terminal-only dependencies."""

import shutil
import textwrap
from typing import IO


def write_report_line(output: IO[str], text: str = "") -> None:
    """Wrap long labels and paths while retaining their complete values."""
    width = max(40, shutil.get_terminal_size(fallback=(88, 24)).columns)
    output.write(textwrap.fill(text, width=width, subsequent_indent="  ") + "\n")
