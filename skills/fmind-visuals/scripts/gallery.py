"""Build a numbered, self-contained contact sheet of visual variants on light and dark surfaces."""

import argparse
import base64
import html
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KINDS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
LIMIT = 15 * 1024 * 1024  # Keep the sheet small enough to send or open anywhere.
NUMBER = re.compile(r"^v(\d+)", re.IGNORECASE)
CHROMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
COLUMNS = 3
STYLE = """
body { margin: 0; padding: 24px; background: #F8F9FA; color: #202124;
  font-family: "Google Sans", Roboto, "Segoe UI", Helvetica, Arial, sans-serif; }
h1 { margin: 0 0 16px; font-size: 20px; }
.grid { display: grid; grid-template-columns: repeat(COLUMNS, minmax(0, 1fr)); gap: 16px; }
figure { margin: 0; background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 12px; overflow: hidden; }
.pair { display: grid; grid-template-columns: 1fr 1fr; }
.pair div { height: 180px; display: flex; align-items: center; justify-content: center; padding: 12px; }
.light { background: #FFFFFF; } .dark { background: #202124; }
img { max-width: 100%; max-height: 100%; object-fit: contain; }
figcaption { padding: 8px 12px; font-size: 14px; border-top: 1px solid #DADCE0; }
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


def sheet(folder: Path, title: str) -> str:
    items = variants(folder)
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
        kind = "image/svg+xml" if path.suffix.lower() == ".svg" else mimetypes.guess_type(path.name)[0]
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


def chrome() -> str:
    candidates = [os.environ.get("CHROME", ""), *(shutil.which(name) or "" for name in CHROMES), MAC_CHROME]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("no Chrome or Chromium found; set CHROME or open the HTML sheet instead")


def screenshot(page: Path, count: int) -> Path:
    shot = page.with_suffix(".png")
    height = 80 + math.ceil(count / COLUMNS) * 240
    binary = chrome()
    with tempfile.TemporaryDirectory() as profile:
        completed = subprocess.run(  # noqa: S603 - fixed browser binary and a local file URL
            [
                binary,
                "--headless=new",
                "--hide-scrollbars",
                "--disable-gpu",
                f"--user-data-dir={profile}",
                f"--window-size=1440,{height}",
                f"--screenshot={shot}",
                page.resolve().as_uri(),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
            check=False,
        )
    if completed.returncode or not shot.exists():
        tail = " ".join(completed.stderr.decode("utf-8", "replace").split())[-300:]
        raise RuntimeError(f"{Path(binary).name} failed to screenshot the sheet (exit {completed.returncode}): {tail}")
    return shot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder holding the variant files")
    parser.add_argument("--title", default="Variants", help="sheet heading")
    parser.add_argument("--png", action="store_true", help="also screenshot the sheet with Chrome or Chromium")
    args = parser.parse_args(argv)
    try:
        page = args.folder / "gallery.html"
        page.write_text(sheet(args.folder, args.title), encoding="utf-8")
        sys.stdout.write(f"Wrote {page} with {len(variants(args.folder))} variants.\n")
        if args.png:
            sys.stdout.write(f"Wrote {screenshot(page, len(variants(args.folder)))}.\n")
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        sys.stderr.write(f"Gallery error: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
