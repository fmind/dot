"""Build a numbered, self-contained contact sheet of visual variants on light and dark surfaces."""

import argparse
import base64
import html
import importlib.util
import math
import re
import subprocess
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

# Reuse the sibling SVG checker's Chrome discovery and isolated screenshot.
SVG_CHECKER = Path(__file__).resolve().parents[2] / "svg/scripts/check_svg.py"
MIME_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
KINDS = set(MIME_TYPES)
LIMIT = 15 * 1024 * 1024  # Keep the sheet small enough to send or open anywhere.
NUMBER = re.compile(r"^v(\d+)", re.IGNORECASE)
COLUMNS = 3
STYLE = """
body { margin: 0; padding: 24px; background: #F1F3F4; color: #202124;
  font-family: "Google Sans", Roboto, "Segoe UI", Helvetica, Arial, sans-serif; }
h1 { margin: 0 0 16px; font-size: 20px; }
.grid { display: grid; grid-template-columns: repeat(COLUMNS, minmax(0, 1fr)); gap: 16px; }
figure { margin: 0; background: #FFFFFF; border: 1px solid #9AA0A6; border-radius: 12px; overflow: hidden; }
.pair { display: grid; grid-template-columns: 1fr 1fr; }
.pair div { height: 180px; display: flex; align-items: center; justify-content: center; padding: 12px; }
.light { background: #FFFFFF; } .dark { background: #202124; }
img { max-width: 100%; max-height: 100%; object-fit: contain; }
figcaption { padding: 8px 12px; font-size: 14px; border-top: 1px solid #9AA0A6; }
b { color: #174EA6; margin-right: 8px; }
"""


def variants(folder: Path) -> list[tuple[str, Path]]:
    """Return (label, path) pairs: vNN prefixes keep their number across rounds, others count in name order."""
    files = sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in KINDS and path.stem != "gallery"  # skip our own screenshot
    )
    if not files:
        raise ValueError(f"no {', '.join(sorted(KINDS))} files in {folder}")
    labels = []
    for index, path in enumerate(files, 1):
        match = NUMBER.match(path.stem)
        labels.append((f"v{int(match.group(1)):02d}" if match else f"#{index}", path))
    return labels


def sheet(folder: Path, title: str, items: list[tuple[str, Path]] | None = None) -> str:
    items = items or variants(folder)
    # Each image is embedded twice as base64 (4/3 each), so the page is at least 8/3 of the inputs:
    # fail before reading them when even that floor is over the limit.
    total = sum(path.stat().st_size for _, path in items)
    if total * 8 // 3 > LIMIT:
        raise ValueError(
            f"variants total {total} bytes and embed as at least {total * 8 // 3} bytes, "
            f"over the {LIMIT}-byte sheet limit; split the folder"
        )
    figures = []
    for label, path in items:
        kind = MIME_TYPES[path.suffix.lower()]
        source = f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"
        image = f'<img src="{source}" alt="{html.escape(path.name)}">'
        figures.append(
            f'<figure><div class="pair"><div class="light">{image}</div><div class="dark">{image}</div></div>'
            f"<figcaption><b>{label}</b>{html.escape(path.name)}</figcaption></figure>"
        )
    page = (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
        f"<style>{STYLE.replace('COLUMNS', str(COLUMNS))}</style></head>"
        f'<body><h1>{html.escape(title)}</h1><div class="grid">{"".join(figures)}</div></body></html>\n'
    )
    size = len(page.encode())  # the limit applies to the file written, not its inputs
    if size > LIMIT:
        raise ValueError(f"sheet is {size} bytes, over the {LIMIT}-byte limit; split the folder")
    return page


@cache
def svg_checker() -> ModuleType:
    """Load the shared diagrams-as-code SVG checker module."""
    spec = importlib.util.spec_from_file_location("check_svg", SVG_CHECKER)
    if spec is None or spec.loader is None or not SVG_CHECKER.is_file():
        raise RuntimeError(f"SVG checker not found at {SVG_CHECKER}; open the HTML sheet instead")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def screenshot(page: Path, count: int) -> Path:
    """Screenshot the sheet with headless Chrome, scripts and network blocked; a failed run keeps the old PNG."""
    height = 80 + math.ceil(count / COLUMNS) * 240
    return svg_checker().screenshot(page, page.with_suffix(".png"), 1440, height)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("folder", type=Path, help="folder holding the variant files")
    parser.add_argument("--title", default="Variants", help="sheet heading")
    parser.add_argument("--png", action="store_true", help="also screenshot the sheet with Chrome or Chromium")
    args = parser.parse_args(argv)
    try:
        items = variants(args.folder)
        page = args.folder / "gallery.html"
        page.write_text(sheet(args.folder, args.title, items), encoding="utf-8")
        sys.stdout.write(f"Wrote {page} with {len(items)} variants.\n")
        if args.png:
            sys.stdout.write(f"Wrote {screenshot(page, len(items))}.\n")
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        sys.stderr.write(f"Gallery error: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
