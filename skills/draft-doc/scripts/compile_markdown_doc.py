"""Compile and validate Google Docs native Markdown (.md) with Typst, Mermaid, and SVG figures."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

# Reuse the diagrams-as-code SVG contract checker; it sits beside this package in the skill catalog.
SVG_CHECKER = Path(__file__).resolve().parents[2] / "diagrams-as-code/references/svg/scripts/check_svg.py"
# Pinned Mermaid CLI, run through `mise exec` so no global install is needed. chromium-bidi is published
# without trusted-publisher evidence; this exact version was reviewed on 2026-10-23 (diagrams-as-code mermaid.md).
MERMAID_CLI = "npm:@mermaid-js/mermaid-cli[trust_policy_excludes=chromium-bidi@157.0.8090-0]@12.2.0"
MAX_SCALE = 4
# Google Docs displays an embedded PNG at 0.75 pt per pixel and ignores its pHYs density (verified 2026-10-28),
# so cap figures at 600 px (450 pt), which fits the Letter and A4 text columns.
MAX_FIGURE_WIDTH_PX = 600
# Draw SVG figures on a canvas as wide as the cap so they embed at 1:1 and 12 px labels read at 9 pt.
SVG_CANVAS_WIDTH = float(MAX_FIGURE_WIDTH_PX)

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"(?m)^(`{3,}|~{3,})([^\r\n]*)\r?\n(.*?)\r?\n\1[ \t]*\r?$", re.DOTALL)
GITHUB_ALERT_RE = re.compile(r"(?m)^[ \t]*>[ \t]*\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]")
# HTML comments also render as literal text in native .md (verified 2026-10-28).
RAW_HTML_RE = re.compile(
    r"<!--|</?(?:details|summary|mark|u|br|div|span|table|thead|tbody|tr|td|th|img|script|iframe|style)\b[^>]*>",
    re.IGNORECASE,
)
# CommonMark setext headings: a paragraph line directly followed by a `---` or `===` underline. A list item,
# blockquote, table row, or indented code line cannot become one, because the underline is never a lazy
# continuation line (https://spec.commonmark.org/0.31.2/#setext-headings).
SETEXT_UNDERLINE_RE = re.compile(r" {0,3}(?:-+|=+)[ \t]*")
SINGLE_LINE_BLOCK_RE = re.compile(r" {0,3}(?:#{1,6}(?:[ \t]|$)|([-*_])(?:[ \t]*\1){2,}[ \t]*$)")
NON_PARAGRAPH_START_RE = re.compile(r"(?: {0,3}(?:>|\||[-+*](?:[ \t]|$)|\d{1,9}[.)](?:[ \t]|$))| {4}|\t)")
# The compiler reads fences at column 0 only; an indented mermaid fence would reach Docs as a code block.
INDENTED_MERMAID_RE = re.compile(r"(?mi)^[ \t]+(?:`{3,}|~{3,})[ \t]*mermaid(?:[ \t]|$)")
SVG_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+\.svg)\)")
TYP_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+\.typ)\)")
LOCAL_FIGURE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+\.(?:svg|typ))\)")
# Image links the compiler does not read from disk.
NON_LOCAL_PREFIXES = ("http://", "https://", "data:")
MERMAID_ALT_RE = re.compile(r"^\s*%%\s*alt\s*:\s*(.+?)\s*$", re.MULTILINE)
CAPTION_LINE_RE = re.compile(r"^\s*(?:\*([^*\r\n]+)\*|_([^_\r\n]+)_)\s*$")
INLINE_CODE_RE = re.compile(r"`[^`\r\n]+`")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")


def _clean_alt(text: str) -> str:
    """Flatten Markdown links and replace remaining square brackets so `![alt][id]` stays valid."""
    return MD_LINK_RE.sub(r"\1", text).replace("[", "(").replace("]", ")").strip()


ASSET_MIME_TYPES = {
    ".md": "text/markdown",
    ".mmd": "text/plain",
    ".svg": "image/svg+xml",
    ".typ": "text/plain",
    ".png": "image/png",
}


@cache
def svg_checker() -> ModuleType:
    """Load the shared diagrams-as-code SVG checker module."""
    spec = importlib.util.spec_from_file_location("check_svg", SVG_CHECKER)
    if spec is None or spec.loader is None or not SVG_CHECKER.is_file():
        msg = f"SVG checker not found at {SVG_CHECKER}; install the diagrams-as-code skill beside draft-doc."
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def check_svg(path: Path, expected_width: float = SVG_CANVAS_WIDTH) -> list[str]:
    """Validate an SVG figure with the diagrams-as-code contract (security, accessibility, fonts, viewBox)."""
    if not path.is_file():
        return [f"{path}: SVG file not found"]
    return [f"{path}: {problem}" for problem in svg_checker().check(path, expected_width)]


def _has_setext_heading(markdown: str) -> bool:
    """Return True when a paragraph line is directly followed by a setext underline."""
    block_start: str | None = None  # first line of the current paragraph-like block
    for line in markdown.splitlines():
        if block_start is not None and SETEXT_UNDERLINE_RE.fullmatch(line):
            if not NON_PARAGRAPH_START_RE.match(block_start):
                return True
            block_start = None  # under a list item, blockquote, or table, `---` is a thematic break
        elif not line.strip() or SINGLE_LINE_BLOCK_RE.match(line):
            block_start = None
        elif block_start is None or NON_PARAGRAPH_START_RE.match(line):
            block_start = line
    return False


def check_markdown_dialect(markdown: str) -> list[str]:
    """Check Markdown text against Google Docs native .md dialect constraints."""
    problems: list[str] = []
    if FRONTMATTER_RE.search(markdown):
        problems.append(
            "YAML frontmatter (--- ... ---) is unsupported in Google Docs native .md (renders as a giant HEADING_2); "
            "use metadata lines or a bold subtitle line below `# Title` instead."
        )

    outside_fences = FENCED_BLOCK_RE.sub("", markdown)
    outside_code = INLINE_CODE_RE.sub("code", outside_fences)

    if GITHUB_ALERT_RE.search(outside_code):
        problems.append(
            "GitHub Alert syntax (`> [!IMPORTANT]`, `> [!WARNING]`, etc.) renders as literal text in Google Docs; "
            "use a bold blockquote (`> **Important:** ...`) instead."
        )

    if _has_setext_heading(outside_code):
        problems.append(
            "Setext heading underline (`---` or `===` directly below a paragraph line) turns that line into a heading; "
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
    if INDENTED_MERMAID_RE.search(outside_fences):
        problems.append(
            "Indented ```mermaid block found (for example under a list item); the compiler only reads fences "
            "at column 0, so unindent its opening and closing fence lines."
        )
    svg_links = [match.group(2) for match in SVG_IMAGE_RE.finditer(outside_code)]
    if any(link.startswith(NON_LOCAL_PREFIXES) for link in svg_links):
        problems.append(
            "Remote .svg image link found; remote SVG images are unsupported: download the file next to the "
            "document and link it by its local path, or use a PNG instead."
        )
    if any(not link.startswith(NON_LOCAL_PREFIXES) for link in svg_links):
        problems.append(
            "Uncompiled .svg image link found; compile it to a Base64 PNG reference with compile_markdown_doc.py."
        )
    typ_links = [match.group(2) for match in TYP_IMAGE_RE.finditer(outside_code)]
    if any(link.startswith(NON_LOCAL_PREFIXES) for link in typ_links):
        problems.append(
            "Remote .typ image link found; remote Typst sources are unsupported: download the file next to the "
            "document and link it by its local path, or use a PNG instead."
        )
    if any(not link.startswith(NON_LOCAL_PREFIXES) for link in typ_links):
        problems.append(
            "Uncompiled .typ image link found; compile it to a Base64 PNG reference with compile_markdown_doc.py."
        )
    return problems


def render_svg_png(svg_path: Path, out_png: Path, scale: float = 2, max_width_px: int | None = None) -> tuple[int, int]:
    """Rasterize an SVG file to a PNG with headless Chrome at its viewBox size, optionally capped in width."""
    checker = svg_checker()
    root = ET.parse(svg_path).getroot()  # noqa: S314 - already checked local SVG file
    width, height = checker.view_box(root) or (SVG_CANVAS_WIDTH, SVG_CANVAS_WIDTH * 9 / 16)
    w_px, h_px = math.ceil(width), math.ceil(height)
    if max_width_px:
        scale = min(scale, max_width_px / w_px)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    checker.screenshot(svg_path, out_png, w_px, h_px, scale=scale)
    return png_size(out_png)


def png_size(path: Path) -> tuple[int, int]:
    """Return (width, height) in pixels from a PNG file's IHDR header."""
    header = path.read_bytes()[:24]
    if not header.startswith(b"\x89PNG\r\n\x1a\n") or header[12:16] != b"IHDR":
        msg = f"{path.name} is not a PNG file"
        raise ValueError(msg)
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _typst_command() -> tuple[list[str], int]:
    """Return the Typst CLI command and timeout: `typst` on PATH, else `mise exec typst`."""
    if typst := shutil.which("typst"):
        return [typst], 60
    if mise := shutil.which("mise"):
        return [mise, "exec", "--quiet", "typst", "--", "typst"], 180
    msg = "Neither `typst` nor `mise` is on PATH; install typst (e.g. `mise install typst`) to compile .typ figures."
    raise RuntimeError(msg)


def render_typst_png(
    typ_path: Path,
    out_png: Path,
    scale: float = 2,
    max_width_px: int | None = None,
    root_dir: Path | None = None,
) -> tuple[int, int]:
    """Compile a single-page Typst figure to PNG, failing on font warnings and capping width when requested."""
    command, timeout = _typst_command()
    resolved_root = (root_dir or typ_path.parent).resolve()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    ppi = 96.0 * scale
    width = 0
    for _ in range(3):
        out_png.unlink(missing_ok=True)
        proc = subprocess.run(  # noqa: S603 - fixed CLI command and local paths
            [
                *command,
                "compile",
                "--root",
                str(resolved_root),
                "--format",
                "png",
                "--ppi",
                f"{ppi:g}",
                str(typ_path),
                str(out_png.resolve()),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        if proc.returncode != 0 or not out_png.is_file() or out_png.stat().st_size == 0:
            msg = f"typst failed to compile {typ_path.name} (exit {proc.returncode}): {detail}"
            raise RuntimeError(msg)
        if proc.stderr.strip():
            msg = f"typst emitted warnings while compiling {typ_path.name}: {detail}"
            raise RuntimeError(msg)
        width, height = png_size(out_png)
        if not max_width_px or width <= max_width_px:
            return width, height
        ppi *= max_width_px / width
    msg = f"Typst PNG stayed {width}px wide after rescaling; the cap is {max_width_px}px, so narrow or split {typ_path.name}"
    raise RuntimeError(msg)


def _mmdc_command() -> tuple[list[str], int]:
    """Return the Mermaid CLI command and timeout: the pinned CLI through mise, else `mmdc` on PATH."""
    # Prefer mise: once installed, mise leaves an `mmdc` shim on PATH that fails outside a project that pins it.
    if mise := shutil.which("mise"):
        # The first run installs the pinned CLI into mise's cache; later runs reuse it.
        return [mise, "exec", "--quiet", MERMAID_CLI, "--", "mmdc"], 300
    if mmdc := shutil.which("mmdc"):
        return [mmdc], 60
    msg = "Neither `mise` nor `mmdc` is on PATH; install mise (https://mise.jdx.dev) to run the pinned Mermaid CLI."
    raise RuntimeError(msg)


def render_mermaid_png(mermaid_code: str, out_png: Path, scale: float = 2, max_width_px: int | None = None) -> None:
    """Render a Mermaid diagram string to PNG with the Mermaid CLI and system Chrome, optionally capped in width."""
    command, timeout = _mmdc_command()
    chrome_bin = os.environ.get("PUPPETEER_EXECUTABLE_PATH") or svg_checker().chrome()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mmd-render-") as tmp:
        mmd_file = Path(tmp) / "diagram.mmd"
        mmd_file.write_text(mermaid_code.strip() + "\n", encoding="utf-8")
        env = {**os.environ, "PUPPETEER_EXECUTABLE_PATH": chrome_bin}
        width = 0
        for _ in range(3):  # the width is known only after a render; padding can need one more pass
            out_png.unlink(missing_ok=True)
            proc = subprocess.run(  # noqa: S603 - fixed CLI command and local temp paths
                [
                    *command,
                    "-i",
                    str(mmd_file),
                    "-o",
                    str(out_png.resolve()),
                    "-s",
                    f"{scale:g}",
                    "-b",
                    "white",
                    "--quiet",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                check=False,
            )
            if proc.returncode != 0 or not out_png.is_file() or out_png.stat().st_size == 0:
                detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
                msg = f"mmdc failed to render Mermaid block (exit {proc.returncode}): {detail}"
                raise RuntimeError(msg)
            width = png_size(out_png)[0]
            if not max_width_px or width <= max_width_px:
                return
            scale *= max_width_px / width
    msg = f"Mermaid PNG stayed {width}px wide after rescaling; the cap is {max_width_px}px, so split or simplify the diagram"
    raise RuntimeError(msg)


def compile_markdown(
    source_text: str,
    base_dir: Path,
    *,
    scale: int = 2,
    svg_width: float = SVG_CANVAS_WIDTH,
    assets_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Compile fenced ```mermaid blocks and local .svg / .typ image links into Base64 PNG references."""
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
                alt_text = _clean_alt(alt_match.group(1))
            elif caption_match:
                alt_text = _clean_alt(caption_match.group(1) or caption_match.group(2) or "")
            else:
                alt_text = ""
            alt_text = alt_text or f"Figure {fig_counter} — Architecture diagram"

            png_path = tmp_dir / f"{fig_id}.png"
            render_mermaid_png(raw_code, png_path, scale=scale, max_width_px=MAX_FIGURE_WIDTH_PX)
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

        fig_pieces: list[str] = []
        last_fig_idx = 0
        claimed_asset_names: set[str] = set()
        resolved_base = base_dir.resolve()
        for match in LOCAL_FIGURE_RE.finditer(intermediate):
            if _in_code(match.start()):
                continue
            fig_rel = match.group(2)
            if fig_rel.startswith(NON_LOCAL_PREFIXES):
                continue  # the dialect check below rejects it as unsupported
            fig_path = (base_dir / fig_rel).resolve()
            is_typ = fig_path.suffix.lower() == ".typ"
            kind_label = "Typst" if is_typ else "SVG"
            if not fig_path.is_relative_to(resolved_base):
                raise ValueError(f"{kind_label} path escapes document directory: {fig_rel}")
            if is_typ:
                if not fig_path.is_file():
                    raise ValueError(f"{fig_path}: Typst file not found")
            else:
                svg_problems = check_svg(fig_path, expected_width=svg_width)
                if svg_problems:
                    raise ValueError("; ".join(svg_problems))

            fig_id = next_fig_id()
            alt_text = _clean_alt(match.group(1)) or f"Figure {fig_counter}"
            png_path = tmp_dir / f"{fig_id}.png"
            if is_typ:
                render_typst_png(
                    fig_path,
                    png_path,
                    scale=scale,
                    max_width_px=MAX_FIGURE_WIDTH_PX,
                    root_dir=resolved_base,
                )
            else:
                render_svg_png(fig_path, png_path, scale=scale, max_width_px=MAX_FIGURE_WIDTH_PX)
            b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
            ref_definitions.append(f"[{fig_id}]: <data:image/png;base64,{b64}>")
            fig_entry = {
                "id": fig_id,
                "kind": "typst" if is_typ else "svg",
                "source": str(fig_rel),
                "alt": alt_text,
                "bytes": png_path.stat().st_size,
            }
            if assets_dir is not None:
                # Prefix only a name already taken by another figure in this run; a previous run's copy is overwritten.
                src_asset = assets_dir / fig_path.name
                if src_asset.name in claimed_asset_names and src_asset.resolve() != fig_path.resolve():
                    src_asset = assets_dir / f"{fig_id}-{fig_path.name}"
                claimed_asset_names.add(src_asset.name)
                if src_asset.resolve() != fig_path.resolve():
                    shutil.copy2(fig_path, src_asset)
                png_asset = assets_dir / f"{fig_id}.png"
                shutil.copy2(png_path, png_asset)
                fig_entry["source_asset"] = str(src_asset)
                fig_entry["png_asset"] = str(png_asset)
                if (
                    is_typ
                    and (theme_file := fig_path.parent / "fmind.typ").is_file()
                    and "fmind.typ" in fig_path.read_text(encoding="utf-8")
                ):
                    theme_asset = assets_dir / "fmind.typ"
                    if theme_asset.resolve() != theme_file.resolve():
                        shutil.copy2(theme_file, theme_asset)
                    claimed_asset_names.add(theme_asset.name)
                    fig_entry["companion_assets"] = [str(theme_asset)]
            figures.append(fig_entry)
            fig_pieces.append(intermediate[last_fig_idx : match.start()])
            fig_pieces.append(f"![{alt_text}][{fig_id}]")
            last_fig_idx = match.end()

        fig_pieces.append(intermediate[last_fig_idx:])
        compiled = "".join(fig_pieces).rstrip() + "\n"

    if ref_definitions:
        compiled = compiled + "\n" + "\n".join(ref_definitions) + "\n"

    problems = check_markdown_dialect(compiled)
    if problems:
        raise ValueError("; ".join(problems))

    return compiled, figures


def _validate_drive_id(value: str, label: str = "Drive ID") -> str:
    """Validate a Google Drive file or folder ID before embedding in API queries."""
    cleaned = value.strip()
    if not DRIVE_ID_RE.fullmatch(cleaned):
        msg = f"Invalid {label}: {value!r}"
        raise ValueError(msg)
    return cleaned


def _escape_drive_q(value: str) -> str:
    """Escape backslashes and single quotes for Google Drive q filter strings."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _slugify_doc(name: str) -> str:
    """Derive a clean Drive assets/<doc-slug> directory name from a document filename."""
    stem = name.removesuffix(".src.md").removesuffix(".gdoc.md").removesuffix(".md")
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-") or "document"


def run_gws(args: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    """Execute a gws CLI command with --format json and return the parsed JSON object."""
    gws_bin = shutil.which("gws")
    if not gws_bin:
        msg = "`gws` not found in PATH; install @googleworkspace/cli (e.g. `mise install`)."
        raise RuntimeError(msg)
    proc = subprocess.run(  # noqa: S603 - fixed gws binary and validated arguments
        [gws_bin, *args, "--format", "json"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        msg = f"gws {' '.join(args[:3])} failed (exit {proc.returncode}): {detail}"
        raise RuntimeError(msg)
    out = proc.stdout.strip()
    if not out:
        return {}
    idx = out.find("{")
    if idx == -1:
        msg = f"gws {' '.join(args[:3])}: expected JSON object on stdout"
        raise RuntimeError(msg)
    try:
        data = json.loads(out[idx:])
    except json.JSONDecodeError as exc:
        msg = f"gws {' '.join(args[:3])}: invalid JSON output ({exc})"
        raise RuntimeError(msg) from exc
    if not isinstance(data, dict):
        msg = f"gws {' '.join(args[:3])}: expected a JSON object"
        raise RuntimeError(msg)
    return data


def _ensure_drive_folder(parent_id: str, folder_name: str, gws_dir: Path) -> str:
    """Find or create a child folder named folder_name inside parent_id."""
    valid_parent = _validate_drive_id(parent_id, "parent folder ID")
    q = (
        "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{valid_parent}' in parents and name = '{_escape_drive_q(folder_name)}'"
    )
    resp = run_gws(
        [
            "drive",
            "files",
            "list",
            "--params",
            json.dumps(
                {
                    "pageSize": 5,
                    "q": q,
                    "supportsAllDrives": True,
                    "includeItemsFromAllDrives": True,
                    "fields": "files(id,name)",
                }
            ),
        ],
        cwd=gws_dir,
    )
    files = resp.get("files") or []
    if files:
        return str(files[0]["id"])
    created = run_gws(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": "id,name"}),
            "--json",
            json.dumps(
                {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [valid_parent],
                }
            ),
        ],
        cwd=gws_dir,
    )
    return str(created["id"])


def _list_folder_files(parent_id: str, gws_dir: Path) -> dict[str, str]:
    """Return {name: file_id} for non-trashed non-folder files directly inside parent_id, across all pages."""
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    q = f"trashed = false and mimeType != 'application/vnd.google-apps.folder' and '{valid_parent}' in parents"
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": q,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    found: dict[str, str] = {}
    while True:
        resp = run_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=gws_dir)
        for item in resp.get("files") or []:
            if "id" in item and "name" in item:
                found.setdefault(str(item["name"]), str(item["id"]))
        if not resp.get("nextPageToken"):
            return found
        params["pageToken"] = resp["nextPageToken"]


def _get_drive_file(file_id: str, gws_dir: Path) -> dict[str, Any]:
    """Return the id, name, and parents of an existing Drive file."""
    params = {"fileId": _validate_drive_id(file_id, "file ID"), "supportsAllDrives": True, "fields": "id,name,parents"}
    return run_gws(["drive", "files", "get", "--params", json.dumps(params)], cwd=gws_dir)


def _upsert_drive_file(
    local_path: Path,
    *,
    name: str,
    content_type: str,
    gws_dir: Path,
    parent_id: str | None = None,
    file_id: str | None = None,
    existing_by_name: dict[str, str] | None = None,
    rename: bool = False,
) -> dict[str, Any]:
    """Create or update a file in Google Drive; updates keep the File ID and rename only when asked."""
    target_id = file_id or (existing_by_name or {}).get(name)
    fields = "id,name,mimeType,version,modifiedTime,webViewLink"
    # gws rejects --upload paths outside its working directory, so stage the file in the run's gws
    # directory and upload it by bare name from there, like every other gws call of the run.
    staged = gws_dir / local_path.name
    if staged.resolve() != local_path.resolve():
        shutil.copyfile(local_path, staged)
    upload = ["--upload", local_path.name, "--upload-content-type", content_type]
    if target_id:
        valid_id = _validate_drive_id(target_id, "file ID")
        params = json.dumps({"fileId": valid_id, "supportsAllDrives": True, "fields": fields})
        body = ["--json", json.dumps({"name": name})] if rename else []
        return run_gws(
            [
                "drive",
                "files",
                "update",
                "--params",
                params,
                *body,
                *upload,
            ],
            cwd=gws_dir,
        )
    if not parent_id:
        msg = f"Cannot create {name!r} without a target Drive folder ID."
        raise ValueError(msg)
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    return run_gws(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": fields}),
            "--json",
            json.dumps({"name": name, "mimeType": content_type, "parents": [valid_parent]}),
            *upload,
        ],
        cwd=gws_dir,
    )


def upload_to_drive(
    compiled_md: Path,
    asset_paths: list[Path],
    *,
    gws_dir: Path,
    drive_folder: str | None = None,
    file_id: str | None = None,
    doc_name: str | None = None,
    doc_slug: str | None = None,
    existing_file: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upload the compiled .md file and its assets/<doc-slug>/ bundle to Google Drive.

    gws loads a `.env` from its working directory upward, so every gws call runs from gws_dir, a private
    directory: metadata reads, uploads, and read-backs then resolve the same account.
    """
    if not drive_folder and not file_id:
        msg = "Provide --drive-folder <FOLDER_ID> and/or --file-id <FILE_ID> to upload to Google Drive."
        raise ValueError(msg)

    parent_folder_id = _validate_drive_id(drive_folder, "folder ID") if drive_folder else None
    resolved_name = doc_name or compiled_md.name
    if file_id:
        # Keep the live document's name and location unless --doc-name asks for a rename.
        existing = existing_file or _get_drive_file(file_id, gws_dir)
        if not parent_folder_id and existing.get("parents"):
            parent_folder_id = _validate_drive_id(str(existing["parents"][0]), "folder ID")
        if not doc_name and existing.get("name"):
            resolved_name = str(existing["name"])
    if not resolved_name.endswith(".md"):
        resolved_name = f"{resolved_name}.md"

    resolved_slug = doc_slug or _slugify_doc(resolved_name)
    existing_in_parent = _list_folder_files(parent_folder_id, gws_dir) if (parent_folder_id and not file_id) else {}
    doc_result = _upsert_drive_file(
        compiled_md,
        name=resolved_name,
        content_type="text/markdown",
        gws_dir=gws_dir,
        parent_id=parent_folder_id,
        file_id=file_id,
        existing_by_name=existing_in_parent,
        rename=bool(file_id and doc_name),
    )
    uploaded_file_id = str(doc_result["id"])

    assets_folder_id: str | None = None
    uploaded_assets: list[dict[str, Any]] = []
    warning: str | None = None
    if asset_paths and not parent_folder_id:
        # Only reachable with --file-id alone, when Drive lists no `parents` for the file.
        names = ", ".join(path.name for path in asset_paths)
        warning = (
            f"Skipped {len(asset_paths)} asset upload(s) ({names}): Drive returned no parent folder for file "
            f"{uploaded_file_id}, so assets/{resolved_slug}/ has no location; rerun with --drive-folder <FOLDER_ID> "
            "to upload them."
        )
    if parent_folder_id and asset_paths:
        assets_root_id = _ensure_drive_folder(parent_folder_id, "assets", gws_dir)
        assets_folder_id = _ensure_drive_folder(assets_root_id, resolved_slug, gws_dir)
        existing_assets = _list_folder_files(assets_folder_id, gws_dir)
        for asset_path in asset_paths:
            if not asset_path.is_file():
                continue
            mime = ASSET_MIME_TYPES.get(asset_path.suffix.lower(), "application/octet-stream")
            res = _upsert_drive_file(
                asset_path,
                name=asset_path.name,
                content_type=mime,
                gws_dir=gws_dir,
                parent_id=assets_folder_id,
                existing_by_name=existing_assets,
            )
            uploaded_assets.append(
                {
                    "id": res.get("id"),
                    "name": res.get("name", asset_path.name),
                    "mimeType": res.get("mimeType", mime),
                }
            )

    return {
        "file_id": uploaded_file_id,
        "name": doc_result.get("name", resolved_name),
        "docs_url": f"https://docs.google.com/document/d/{uploaded_file_id}/edit",
        "web_view_link": doc_result.get("webViewLink"),
        "assets_folder_id": assets_folder_id,
        "assets_folder_path": f"assets/{resolved_slug}" if assets_folder_id else None,
        "assets_folder_url": f"https://drive.google.com/drive/folders/{assets_folder_id}" if assets_folder_id else None,
        "uploaded_assets": uploaded_assets,
        "warning": warning,
    }


def _scale(value: str) -> int:
    """Parse --scale as an integer from 1 to MAX_SCALE; larger factors only bloat the Base64 payload."""
    try:
        scale = int(value)
    except ValueError:
        scale = 0
    if not 1 <= scale <= MAX_SCALE:
        msg = f"must be an integer from 1 to {MAX_SCALE}, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return scale


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument(
        "source",
        type=Path,
        help="Input .src.md / .md document or .typ / .svg figure to validate/compile.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (.md for compiled Markdown or .png for rendered Typst/SVG).",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Directory to export editable sources (.src.md, .typ, .mmd, .svg) and .png figures for Drive upload.",
    )
    parser.add_argument(
        "--drive-folder",
        type=str,
        default=None,
        help="Google Drive parent folder ID to upload the compiled .md and its assets/<doc-slug>/ bundle.",
    )
    parser.add_argument(
        "--file-id",
        type=str,
        default=None,
        help="Existing Google Drive .md file ID to update in place while syncing assets/<doc-slug>/.",
    )
    parser.add_argument(
        "--doc-name",
        type=str,
        default=None,
        help="Target filename in Google Drive (e.g. 'Nightly Batch Review.md'). Defaults to existing Drive name with --file-id, else output filename.",
    )
    parser.add_argument(
        "--doc-slug",
        type=str,
        default=None,
        help="Subfolder slug under assets/<doc-slug>/ in Google Drive. Defaults to slugified document stem.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate Google Docs .md dialect or SVG rules without rendering.",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=_scale,
        default=2,
        help=f"Device scale factor for PNG rasterization, 1 to {MAX_SCALE} (default: 2).",
    )
    parser.add_argument(
        "--svg-width",
        type=float,
        default=SVG_CANVAS_WIDTH,
        help=f"Expected SVG viewBox width in px (default: {SVG_CANVAS_WIDTH:g}; 0 disables the check).",
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
        elif source.suffix.lower() == ".typ":
            rendered_size = None
            if args.check_only:
                with tempfile.TemporaryDirectory(prefix=".typ-check-") as tmp:
                    rendered_size = render_typst_png(source, Path(tmp) / "check.png", scale=args.scale)
            elif output is not None:
                rendered_size = render_typst_png(source, output, scale=args.scale)
            payload = {
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
                if out_path.resolve() == source.resolve():
                    raise ValueError(f"Output path must differ from source Markdown: {out_path}")
                # One private directory for every gws call of this run: see upload_to_drive.
                with tempfile.TemporaryDirectory(prefix="draft-doc-") as tmp:
                    gws_dir = Path(tmp)
                    existing_file = (
                        _get_drive_file(args.file_id, gws_dir) if args.file_id and not args.doc_name else None
                    )
                    drive_name = args.doc_name or (existing_file or {}).get("name") or out_path.name
                    doc_slug = args.doc_slug or _slugify_doc(str(drive_name))
                    if (args.drive_folder or args.file_id) and assets_dir is None:
                        assets_dir = out_path.parent / "assets" / doc_slug
                    compiled, figures = compile_markdown(
                        text,
                        source.parent,
                        scale=args.scale,
                        svg_width=args.svg_width,
                        assets_dir=assets_dir,
                    )
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(compiled, encoding="utf-8")
                    exported_assets: list[str] = []
                    if assets_dir is not None:
                        src_asset = assets_dir / source.name
                        if src_asset.resolve() != source.resolve():
                            shutil.copy2(source, src_asset)
                        exported_assets.append(str(src_asset))
                        for fig in figures:
                            for extra in fig.get("companion_assets", []):
                                if extra not in exported_assets:
                                    exported_assets.append(extra)
                            for key in ("source_asset", "png_asset"):
                                if fig.get(key) and fig[key] not in exported_assets:
                                    exported_assets.append(fig[key])
                    drive_info: dict[str, Any] | None = None
                    if args.drive_folder or args.file_id:
                        drive_info = upload_to_drive(
                            out_path,
                            [Path(p) for p in exported_assets],
                            drive_folder=args.drive_folder,
                            file_id=args.file_id,
                            doc_name=args.doc_name,
                            doc_slug=doc_slug,
                            existing_file=existing_file,
                            gws_dir=gws_dir,
                        )
                        if warning := drive_info["warning"]:
                            line = json.dumps({"warning": warning}) if args.json_output else f"Warning: {warning}"
                            sys.stderr.write(line + "\n")
                payload = {
                    "status": "ok",
                    "source": str(source),
                    "output": str(out_path),
                    "bytes": len(compiled.encode("utf-8")),
                    "figures": figures,
                    "assets_dir": str(assets_dir) if assets_dir is not None else None,
                    "assets": exported_assets,
                    "drive": drive_info,
                }

        if args.json_output:
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            sys.stdout.write(f"OK {source} -> {payload.get('output') or 'validated'}\n")
    # Expected failures print one line; anything else is a bug and keeps its traceback.
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        if args.json_output:
            sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
