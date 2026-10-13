"""Check hand-authored SVG illustrations against the SVG guide and optionally render review screenshots."""

import argparse
import html
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}href"
MIN_FONT_PX = 12.0
FORBIDDEN = {"script", "foreignObject", "iframe", "object", "embed"}
FONT_SIZE = re.compile(r"font-size\s*:\s*([0-9.]+)(px)?", re.IGNORECASE)
BRAND_FONTS = re.compile(r'"Google Sans( Text| Code)?",\s*')
CHROMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def local(tag: str) -> str:
    return tag.removeprefix(NS)


def view_box(root: ET.Element) -> tuple[float, float] | None:
    parts = (root.get("viewBox") or "").replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        values = tuple(float(part) for part in parts)
    except ValueError:
        return None
    if not all(math.isfinite(value) for value in values) or values[2] <= 0 or values[3] <= 0:
        return None
    return values[2], values[3]


def check(path: Path, width: float) -> list[str]:
    """Return guide violations; an empty list means the static checks pass."""
    try:
        root = ET.parse(path).getroot()  # noqa: S314 - local first-party file; no entity expansion in ElementTree
    except ET.ParseError as error:
        return [f"not well-formed XML: {error}"]
    if local(root.tag) != "svg":
        return [f"root element is <{local(root.tag)}>, not <svg>"]
    problems: list[str] = []
    size = view_box(root)
    if size is None:
        problems.append("missing or invalid viewBox")
    elif width and size[0] != width:
        problems.append(f"viewBox width is {size[0]:g}, expected {width:g}")
    if root.get("role") != "img":
        problems.append('root <svg> needs role="img"')
    ids = Counter(element.get("id") for element in root.iter() if element.get("id"))
    problems += [f"duplicate id {identifier!r}" for identifier, count in ids.items() if count > 1]
    labelled = (root.get("aria-labelledby") or "").split()
    for name in ("title", "desc"):
        element = root.find(NS + name)
        if element is None or not "".join(element.itertext()).strip():
            problems.append(f"missing non-empty <{name}> as a direct child of <svg>")
        elif not element.get("id") or element.get("id") not in labelled:
            problems.append(f"<{name}> needs an id referenced by aria-labelledby")
    if not labelled:
        problems.append("root <svg> needs aria-labelledby pointing at its <title> and <desc>")
    problems += [f"aria-labelledby references missing id {ref!r}" for ref in labelled if ref not in ids]
    for element in root.iter():
        tag = local(element.tag)
        if tag in FORBIDDEN:
            problems.append(f"<{tag}> is ignored or unsafe when the SVG is embedded through <img>")
        href = element.get("href") or element.get(XLINK) or ""
        if tag in {"image", "use", "feImage"} and href and not href.startswith("#"):
            problems.append(f"<{tag}> loads {href[:60]!r}; inline the shape instead of external or raster content")
        css = (element.text or "") if tag == "style" else (element.get("style") or "")
        if tag == "style" and re.search(r"@import|@font-face|url\(\s*['\"]?(https?:|data:)", css, re.IGNORECASE):
            problems.append("<style> imports, embeds fonts, or loads remote URLs; <img> sandboxing drops them")
        sizes = [value for value, _ in FONT_SIZE.findall(css)]
        attribute = element.get("font-size")
        if attribute:
            match = re.fullmatch(r"\s*([0-9.]+)(px)?\s*", attribute)
            sizes += [match.group(1)] if match else []
        for value in sizes:
            try:
                size = float(value)
            except ValueError:
                problems.append(f"<{tag}> uses invalid font-size {value!r}")
                continue
            if size < MIN_FONT_PX:
                problems.append(f"<{tag}> uses font-size {size:g}px, below {MIN_FONT_PX:g}px")
    return problems


def chrome() -> str:
    candidates = [os.environ.get("CHROME", ""), *(shutil.which(name) or "" for name in CHROMES), MAC_CHROME]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("no Chrome or Chromium found; set CHROME or use the playwright skill to screenshot")


def render(path: Path, out: Path) -> list[Path]:
    """Screenshot the SVG as an image with brand fonts and with Google Sans removed."""
    root = ET.parse(path).getroot()  # noqa: S314 - already checked local file
    width, height = view_box(root) or (960.0, 540.0)
    binary = chrome()
    shots = []
    with tempfile.TemporaryDirectory() as workspace:
        temporary = Path(workspace)
        fallback = temporary / "fallback.svg"
        fallback.write_text(BRAND_FONTS.sub("", path.read_text(encoding="utf-8")), encoding="utf-8")
        for source, name in ((path, path.stem), (fallback, f"{path.stem}.fallback")):
            # A top-level SVG is an active document. Only the generated HTML is
            # navigated to; SVG content stays in the browser's inert image context.
            wrapper = temporary / "preview.html"
            wrapper.write_text(
                '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
                "<style>body{margin:0}img{display:block;width:100vw;height:100vh}</style>"
                '</head><body><img alt="" src="'
                + html.escape(source.resolve().as_uri(), quote=True)
                + '"/></body></html>',
                encoding="utf-8",
            )
            shot = out / f"{name}.png"
            completed = subprocess.run(  # noqa: S603 - fixed browser binary and file URLs
                [
                    binary,
                    "--headless=new",
                    "--hide-scrollbars",
                    "--disable-gpu",
                    f"--user-data-dir={temporary / 'profile'}",
                    f"--window-size={math.ceil(width)},{math.ceil(height)}",
                    f"--screenshot={shot}",
                    wrapper.as_uri(),
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=60,
                check=False,
            )
            if completed.returncode or not shot.exists():
                tail = " ".join(completed.stderr.decode("utf-8", "replace").split())[-300:]
                raise RuntimeError(
                    f"{Path(binary).name} failed to render {source.name} (exit {completed.returncode}): {tail}"
                )
            shots.append(shot)
    return shots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", nargs="+", type=Path, help="SVG files to check")
    parser.add_argument("--width", type=float, default=960, help="expected viewBox width; 0 skips the check")
    parser.add_argument("--render", type=Path, metavar="DIR", help="also write brand and fallback-font PNGs to DIR")
    args = parser.parse_args(argv)
    failed = False
    for path in args.svg:
        problems = check(path, args.width) if path.is_file() else ["file not found"]
        failed |= bool(problems)
        for problem in problems:
            sys.stdout.write(f"{path}: {problem}\n")
        if not problems:
            sys.stdout.write(f"{path}: ok\n")
            if args.render:
                args.render.mkdir(parents=True, exist_ok=True)
                try:
                    shots = render(path, args.render)
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                    sys.stderr.write(f"{path}: render error: {error}\n")
                    failed = True
                else:
                    sys.stdout.write("".join(f"{path}: rendered {shot}\n" for shot in shots))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
