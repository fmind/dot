#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""A concise description of what this script does goes here."""

import argparse
import sys
from pathlib import Path

__version__ = "0.1.0"


def existing_file(value: str) -> Path:
    """argparse type: reject a missing input before any work starts."""
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {value}")
    return path


def process(input_file: Path, target: Path) -> None:
    del input_file, target
    # ... do the real work here ...


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("input_file", type=existing_file, metavar="INPUT", help="Path to process")
    parser.add_argument("-o", "--output", type=Path, metavar="DIR", help="Output directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show progress details on stderr")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    target = args.output or args.input_file.parent
    if args.verbose:
        sys.stderr.write(f"Processing {args.input_file} -> {target}\n")
    try:
        process(args.input_file, target)
    except OSError as error:
        sys.stderr.write("Error: Cannot process the file. Check file access and the output directory.\n")
        raise SystemExit(1) from error
    except Exception as error:
        # Exception messages and traceback source lines can contain secrets too: report none of them.
        sys.stderr.write("Error: Processing failed. Check the inputs; if it persists, report the failure.\n")
        raise SystemExit(1) from error
    sys.stdout.write(f"Successfully processed {args.input_file}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
