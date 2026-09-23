#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
#     "typer>=0.27.0",
# ]
# ///

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

__version__ = "0.1.0"
app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
)
err = Console(stderr=True, markup=False, highlight=False, emoji=False)  # stderr: logs and errors
out = Console(markup=False, highlight=False, emoji=False)  # stdout: results


def version_callback(value: bool) -> None:
    """Show the version without requiring an input file."""
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=0)


@app.command(no_args_is_help=True)
def main(
    input_file: Annotated[Path, typer.Argument(help="Path to process", exists=True, dir_okay=False)],
    output_dir: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show progress details")] = False,
    _version: Annotated[
        bool, typer.Option("--version", callback=version_callback, is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    """A concise description of what this script does goes here."""
    try:
        target = output_dir or input_file.parent
        if verbose:
            err.print(f"Processing {input_file} -> {target}", style="dim", soft_wrap=True)
        # ... do the real work here ...
        out.print(f"Successfully processed {input_file}", soft_wrap=True)
    except OSError as exc:
        err.print("Error: Cannot process the file. Check file access and the output directory.")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        # Exception messages and traceback source lines can contain secrets too.
        err.print("Error: Processing failed. Check the inputs; if it persists, report the failure.")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
