"""Compile and validate Google Docs native Markdown (.md) with @2x Mermaid and SVG figures."""

from __future__ import annotations

import argparse
import base64
import json
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
from typing import Any

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
MIN_FONT_PX = 12.0
FORBIDDEN_SVG_TAGS = {"script", "foreignObject", "iframe", "object", "embed"}
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([0-9.]+)(?:px)?\s*(?=[;}\s!]|$)", re.IGNORECASE)
CHROMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"(?m)^(`{3,}|~{3,})([^\n]*)\n(.*?)\n\1[ \t]*$", re.DOTALL)
GITHUB_ALERT_RE = re.compile(r"(?m)^[ \t]*>[ \t]*\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]")
RAW_HTML_RE = re.compile(
    r"</?(?:details|summary|mark|u|br|div|span|table|thead|tbody|tr|td|th|img|script|iframe|style)\b[^>]*>",
    re.IGNORECASE,
)
SETEXT_H2_RE = re.compile(r"(?m)^(?!\s*$)(?![ \t]*[>|#*+-])[^\n|]+\n[ \t]*---+[ \t]*$")
SVG_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+\.svg)\)")
MERMAID_ALT_RE = re.compile(r"^\s*%%\s*alt\s*:\s*(.+?)\s*$", re.MULTILINE)
CAPTION_LINE_RE = re.compile(r"^\s*(?:\*([^*\n]+)\*|_([^_\n]+)_)\s*$")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _local_tag(tag: str) -> str:
    return tag.removeprefix(SVG_NS)


def svg_view_box(root: ET.Element) -> tuple[float, float] | None:
    """Return (width, height) from root <svg viewBox='0 0 W H'> or None if invalid."""
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


def check_svg(path: Path, expected_width: float = 960.0) -> list[str]:
    """Validate an SVG file for security, accessibility, font floor, and viewBox."""
    if not path.is_file():
        return [f"{path}: SVG file not found"]
    try:
        root = ET.parse(path).getroot()  # noqa: S314 - local user/agent SVG; ElementTree does not expand external entities
    except ET.ParseError as exc:
        return [f"{path}: not well-formed XML ({exc})"]
    if _local_tag(root.tag) != "svg":
        return [f"{path}: root element is <{_local_tag(root.tag)}>, expected <svg>"]

    problems: list[str] = []
    size = svg_view_box(root)
    if size is None:
        problems.append(f"{path}: missing or invalid viewBox")
    elif expected_width > 0 and size[0] != expected_width:
        problems.append(f"{path}: viewBox width is {size[0]:g}, expected {expected_width:g}")

    if root.get("role") != "img":
        problems.append(f'{path}: root <svg> needs role="img"')

    ids = Counter(el.get("id") for el in root.iter() if el.get("id"))
    problems.extend(f"{path}: duplicate id {ident!r}" for ident, count in ids.items() if count > 1)

    labelled = (root.get("aria-labelledby") or "").split()
    for name in ("title", "desc"):
        child = root.find(SVG_NS + name)
        if child is None or not "".join(child.itertext()).strip():
            problems.append(f"{path}: missing non-empty <{name}> as a direct child of <svg>")
        elif not child.get("id") or child.get("id") not in labelled:
            problems.append(f"{path}: <{name}> needs an id referenced by aria-labelledby")
    if not labelled:
        problems.append(f"{path}: root <svg> needs aria-labelledby pointing at <title> and <desc>")
    problems.extend(f"{path}: aria-labelledby references missing id {ref!r}" for ref in labelled if ref not in ids)

    for el in root.iter():
        tag = _local_tag(el.tag)
        if tag in FORBIDDEN_SVG_TAGS:
            problems.append(f"{path}: <{tag}> is forbidden in standalone SVG figures")
        for attr, value in el.attrib.items():
            attr_name = attr.rsplit("}", 1)[-1]
            if attr_name.lower().startswith("on"):
                problems.append(f"{path}: <{tag}> has event handler attribute {attr_name!r}")
            if re.sub(r"[\x00-\x20]", "", value).lower().startswith("javascript:"):
                problems.append(f"{path}: <{tag}> has a javascript: URL in {attr_name!r}")
        href = el.get("href") or el.get(XLINK_HREF) or ""
        if tag in {"image", "use", "feImage"} and href and not href.startswith("#"):
            problems.append(f"{path}: <{tag}> loads external/raster href {href[:60]!r}; inline vector shapes instead")
        css = (el.text or "") if tag == "style" else (el.get("style") or "")
        if tag == "style" and re.search(r"@import|@font-face|url\(\s*['\"]?(https?:|data:)", css, re.IGNORECASE):
            problems.append(f"{path}: <style> imports or loads external URLs; use installed/system fonts only")
        sizes = FONT_SIZE_RE.findall(css)
        attr_size = el.get("font-size")
        if attr_size:
            match = re.fullmatch(r"\s*([0-9.]+)(px)?\s*", attr_size)
            if match:
                sizes.append(match.group(1))
        for raw_size in sizes:
            try:
                px = float(raw_size)
            except ValueError:
                problems.append(f"{path}: <{tag}> has invalid font-size {raw_size!r}")
                continue
            if px < MIN_FONT_PX:
                problems.append(f"{path}: <{tag}> uses font-size {px:g}px, below minimum {MIN_FONT_PX:g}px")
    return problems


def check_markdown_dialect(markdown: str) -> list[str]:
    """Check Markdown text against Google Docs native .md dialect constraints."""
    problems: list[str] = []
    if FRONTMATTER_RE.search(markdown):
        problems.append(
            "YAML frontmatter (--- ... ---) is unsupported in Google Docs native .md (renders as a giant HEADING_2); "
            "use metadata lines or a bold subtitle line below `# Title` instead."
        )

    outside_fences = FENCED_BLOCK_RE.sub("", markdown)
    outside_code = INLINE_CODE_RE.sub("", outside_fences)

    if GITHUB_ALERT_RE.search(outside_code):
        problems.append(
            "GitHub Alert syntax (`> [!IMPORTANT]`, `> [!WARNING]`, etc.) renders as literal text in Google Docs; "
            "use a bold blockquote (`> **Important:** ...`) instead."
        )

    if SETEXT_H2_RE.search(outside_code):
        problems.append(
            "Setext H2 underline (`---` directly below a line of text) turns that line into HEADING_2 in Google Docs; "
            "add a blank line before `---` for a horizontal rule or use `## Heading`."
        )

    html_match = RAW_HTML_RE.search(outside_code)
    if html_match:
        problems.append(
            f"Raw HTML tag `{html_match.group(0)}` renders as literal text in Google Docs native .md; "
            "use standard Markdown headings (`## Annex`) and formatting instead."
        )

    for match in FENCED_BLOCK_RE.finditer(markdown):
        info = match.group(2).strip().split()[0].lower() if match.group(2).strip() else ""
        if info == "mermaid":
            problems.append(
                "Uncompiled ```mermaid block found; compile it to a Base64 PNG reference with compile_markdown_doc.py."
            )
    if SVG_IMAGE_RE.search(outside_code):
        problems.append(
            "Uncompiled .svg image link found; compile it to a Base64 PNG reference with compile_markdown_doc.py."
        )
    return problems


def find_chrome() -> str:
    """Locate Google Chrome or Chromium executable for headless rendering."""
    candidates = [
        os.environ.get("CHROME", ""),
        os.environ.get("PUPPETEER_EXECUTABLE_PATH", ""),
        *(shutil.which(name) or "" for name in CHROMES),
        MAC_CHROME,
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    msg = "Google Chrome or Chromium not found; install Google Chrome or set CHROME=/path/to/chrome."
    raise RuntimeError(msg)


def render_svg_png(svg_path: Path, out_png: Path, scale: int = 2) -> tuple[int, int]:
    """Rasterize an SVG file to a PNG using headless Chrome and its viewBox dimensions."""
    root = ET.parse(svg_path).getroot()  # noqa: S314 - already checked local SVG file
    width, height = svg_view_box(root) or (960.0, 540.0)
    w_px, h_px = math.ceil(width), math.ceil(height)
    binary = find_chrome()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        with tempfile.TemporaryDirectory(prefix=".svg-render-") as tmp:
            profile = Path(tmp) / "profile"
            prefs = profile / "Default" / "Preferences"
            prefs.parent.mkdir(parents=True)
            prefs.write_text(
                json.dumps({"profile": {"default_content_setting_values": {"javascript": 2}}}),
                encoding="utf-8",
            )
            try:
                proc = subprocess.run(  # noqa: S603 - fixed browser binary and local file URI
                    [
                        binary,
                        "--headless=new",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-sync",
                        "--hide-scrollbars",
                        "--disable-gpu",
                        "--host-resolver-rules=MAP * ^NOTFOUND",
                        "--no-proxy-server",
                        f"--user-data-dir={profile}",
                        f"--force-device-scale-factor={scale}",
                        "--default-background-color=00000000",
                        f"--window-size={w_px},{h_px}",
                        f"--screenshot={out_png.resolve()}",
                        svg_path.resolve().as_uri(),
                    ],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                if attempt < 2:
                    continue
                msg = f"Chrome timed out rendering {svg_path.name} after 3 attempts"
                raise RuntimeError(msg) from exc
            if proc.returncode != 0 or not out_png.is_file() or out_png.stat().st_size == 0:
                detail = " ".join(proc.stderr.split())[-300:]
                msg = f"Chrome failed to render {svg_path.name} (exit {proc.returncode}): {detail}"
                raise RuntimeError(msg)
            break
    return w_px * scale, h_px * scale


def render_mermaid_png(mermaid_code: str, out_png: Path, scale: int = 2) -> None:
    """Render a Mermaid diagram string to PNG via mmdc (@mermaid-js/mermaid-cli)."""
    mmdc_bin = shutil.which("mmdc")
    if not mmdc_bin:
        msg = "`mmdc` not found in PATH; install @mermaid-js/mermaid-cli (e.g. `mise use -g npm:@mermaid-js/mermaid-cli`)."
        raise RuntimeError(msg)
    chrome_bin = find_chrome()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mmd-render-") as tmp:
        mmd_file = Path(tmp) / "diagram.mmd"
        mmd_file.write_text(mermaid_code.strip() + "\n", encoding="utf-8")
        env = {**os.environ, "PUPPETEER_EXECUTABLE_PATH": chrome_bin}
        proc = subprocess.run(  # noqa: S603 - fixed mmdc binary and local temp paths
            [mmdc_bin, "-i", str(mmd_file), "-o", str(out_png.resolve()), "-s", str(scale), "-b", "white", "--quiet"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0 or not out_png.is_file() or out_png.stat().st_size == 0:
            detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
            msg = f"mmdc failed to render Mermaid block (exit {proc.returncode}): {detail}"
            raise RuntimeError(msg)


def compile_markdown(
    source_text: str,
    base_dir: Path,
    *,
    scale: int = 2,
    svg_width: float = 960.0,
    assets_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Compile fenced ```mermaid blocks and local .svg image links into Base64 PNG references."""
    figures: list[dict[str, Any]] = []
    ref_definitions: list[str] = []
    fig_counter = 0
    if assets_dir is not None:
        assets_dir.mkdir(parents=True, exist_ok=True)

    def next_fig_id() -> str:
        nonlocal fig_counter
        fig_counter += 1
        while f"[fig-{fig_counter}]:" in source_text:
            fig_counter += 1
        return f"fig-{fig_counter}"

    with tempfile.TemporaryDirectory(prefix=".gdoc-md-") as tmp:
        tmp_dir = Path(tmp)

        pieces: list[str] = []
        last_idx = 0
        for match in FENCED_BLOCK_RE.finditer(source_text):
            info = match.group(2).strip().split()[0].lower() if match.group(2).strip() else ""
            if info != "mermaid":
                continue
            pieces.append(source_text[last_idx : match.start()])
            raw_code = match.group(3)
            alt_match = MERMAID_ALT_RE.search(raw_code)
            after_text = source_text[match.end() :].lstrip("\r\n")
            first_after_line = after_text.splitlines()[0] if after_text else ""
            caption_match = CAPTION_LINE_RE.match(first_after_line)

            fig_id = next_fig_id()
            if alt_match:
                alt_text = alt_match.group(1).strip()
            elif caption_match:
                alt_text = (caption_match.group(1) or caption_match.group(2) or "").strip()
            else:
                alt_text = f"Figure {fig_counter} — Architecture diagram"

            png_path = tmp_dir / f"{fig_id}.png"
            render_mermaid_png(raw_code, png_path, scale=scale)
            b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
            ref_definitions.append(f"[{fig_id}]: <data:image/png;base64,{b64}>")
            fig_entry: dict[str, Any] = {
                "id": fig_id,
                "kind": "mermaid",
                "alt": alt_text,
                "bytes": png_path.stat().st_size,
            }
            if assets_dir is not None:
                mmd_asset = assets_dir / f"{fig_id}.mmd"
                png_asset = assets_dir / f"{fig_id}.png"
                mmd_asset.write_text(raw_code.strip() + "\n", encoding="utf-8")
                shutil.copy2(png_path, png_asset)
                fig_entry["source_asset"] = str(mmd_asset)
                fig_entry["png_asset"] = str(png_asset)
            figures.append(fig_entry)
            pieces.append(f"![{alt_text}][{fig_id}]")
            last_idx = match.end()

        pieces.append(source_text[last_idx:])
        intermediate = "".join(pieces)

        code_spans = [
            *(m.span() for m in FENCED_BLOCK_RE.finditer(intermediate)),
            *(m.span() for m in INLINE_CODE_RE.finditer(intermediate)),
        ]

        def _in_code(pos: int) -> bool:
            return any(start <= pos < end for start, end in code_spans)

        svg_pieces: list[str] = []
        last_svg_idx = 0
        for match in SVG_IMAGE_RE.finditer(intermediate):
            if _in_code(match.start()):
                continue
            svg_rel = match.group(2)
            if svg_rel.startswith(("http://", "https://", "data:")):
                continue
            svg_path = (base_dir / svg_rel).resolve()
            svg_problems = check_svg(svg_path, expected_width=svg_width)
            if svg_problems:
                raise ValueError("; ".join(svg_problems))

            fig_id = next_fig_id()
            alt_text = match.group(1).strip() or f"Figure {fig_counter}"
            png_path = tmp_dir / f"{fig_id}.png"
            render_svg_png(svg_path, png_path, scale=scale)
            b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
            ref_definitions.append(f"[{fig_id}]: <data:image/png;base64,{b64}>")
            fig_entry = {
                "id": fig_id,
                "kind": "svg",
                "source": str(svg_rel),
                "alt": alt_text,
                "bytes": png_path.stat().st_size,
            }
            if assets_dir is not None:
                svg_asset = assets_dir / svg_path.name
                if svg_asset.exists() and svg_asset.resolve() != svg_path.resolve():
                    svg_asset = assets_dir / f"{fig_id}-{svg_path.name}"
                if svg_asset.resolve() != svg_path.resolve():
                    shutil.copy2(svg_path, svg_asset)
                png_asset = assets_dir / f"{fig_id}.png"
                shutil.copy2(png_path, png_asset)
                fig_entry["source_asset"] = str(svg_asset)
                fig_entry["png_asset"] = str(png_asset)
            figures.append(fig_entry)
            svg_pieces.append(intermediate[last_svg_idx : match.start()])
            svg_pieces.append(f"![{alt_text}][{fig_id}]")
            last_svg_idx = match.end()

        svg_pieces.append(intermediate[last_svg_idx:])
        compiled = "".join(svg_pieces).rstrip() + "\n"

    if ref_definitions:
        compiled = compiled + "\n" + "\n".join(ref_definitions) + "\n"

    problems = check_markdown_dialect(compiled)
    if problems:
        raise ValueError("; ".join(problems))

    return compiled, figures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Input .src.md / .md document or .svg figure to validate/compile.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (.md for compiled Markdown or .png for rendered SVG).",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Optional directory to export editable sources (.src.md, .mmd, .svg) and @2x .png figures for Drive upload.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate Google Docs .md dialect or SVG rules without rendering.",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=int,
        default=2,
        help="Device scale factor for PNG rasterization (default: 2).",
    )
    parser.add_argument(
        "--svg-width",
        type=float,
        default=960.0,
        help="Expected SVG viewBox width in px (0 disables width check).",
    )
    parser.add_argument(
        "-j",
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit machine-readable JSON on stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    source: Path = args.source
    output: Path | None = args.output
    assets_dir: Path | None = args.assets_dir
    try:
        if not source.is_file():
            msg = f"File not found: {source}"
            raise FileNotFoundError(msg)

        if source.suffix.lower() == ".svg":
            problems = check_svg(source, expected_width=args.svg_width)
            if problems:
                raise ValueError("; ".join(problems))
            rendered_size: tuple[int, int] | None = None
            if not args.check_only and output is not None:
                rendered_size = render_svg_png(source, output, scale=args.scale)
            payload: dict[str, Any] = {
                "status": "ok",
                "source": str(source),
                "output": str(output) if output else None,
                "dimensions_px": list(rendered_size) if rendered_size else None,
            }
        else:
            text = source.read_text(encoding="utf-8")
            if args.check_only:
                problems = check_markdown_dialect(text)
                if problems:
                    raise ValueError("; ".join(problems))
                payload = {"status": "ok", "source": str(source), "figures": []}
            else:
                out_path = output or source.with_name(
                    source.name.removesuffix(".src.md") + ".md"
                    if source.name.endswith(".src.md")
                    else f"{source.stem}.gdoc.md"
                )
                compiled, figures = compile_markdown(
                    text,
                    source.parent,
                    scale=args.scale,
                    svg_width=args.svg_width,
                    assets_dir=assets_dir,
                )
                out_path.write_text(compiled, encoding="utf-8")
                exported_assets: list[str] = []
                if assets_dir is not None:
                    src_asset = assets_dir / source.name
                    if src_asset.resolve() != source.resolve():
                        shutil.copy2(source, src_asset)
                    exported_assets.append(str(src_asset))
                    for fig in figures:
                        for key in ("source_asset", "png_asset"):
                            if fig.get(key) and fig[key] not in exported_assets:
                                exported_assets.append(fig[key])
                payload = {
                    "status": "ok",
                    "source": str(source),
                    "output": str(out_path),
                    "bytes": len(compiled.encode("utf-8")),
                    "figures": figures,
                    "assets_dir": str(assets_dir) if assets_dir is not None else None,
                    "assets": exported_assets,
                }

        if args.json_output:
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            sys.stdout.write(f"OK {source} -> {payload.get('output') or 'validated'}\n")
    except Exception as exc:
        if args.json_output:
            sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
