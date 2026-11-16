"""Render and validate Typst, Mermaid, and SVG figures into width-bounded PNG assets."""

from __future__ import annotations

import importlib.util
import math
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path
from types import ModuleType

# Reuse the diagrams-as-code SVG contract checker; it sits beside this package in the skill catalog.
SVG_CHECKER = Path(__file__).resolve().parents[2] / "diagrams-as-code/references/svg/scripts/check_svg.py"
# Pinned Mermaid CLI, run through `mise exec` so no global install is needed. chromium-bidi is published
# without trusted-publisher evidence; this exact version was reviewed on 2026-10-23 (diagrams-as-code mermaid.md).
MERMAID_CLI = "npm:@mermaid-js/mermaid-cli[trust_policy_excludes=chromium-bidi@157.0.8090-0]@12.2.0"
# Google Docs displays an embedded PNG at 0.75 pt per pixel and ignores its pHYs density (verified 2026-10-28),
# so cap figures at 600 px (450 pt), which fits the Letter and A4 text columns.
MAX_FIGURE_WIDTH_PX = 600
# Draw SVG figures on a canvas as wide as the cap so they embed at 1:1 and 12 px labels read at 9 pt.
SVG_CANVAS_WIDTH = float(MAX_FIGURE_WIDTH_PX)


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


def png_size(path: Path) -> tuple[int, int]:
    """Return (width, height) in pixels from a PNG file's IHDR header."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n") or header[12:16] != b"IHDR":
        msg = f"{path.name} is not a PNG file"
        raise ValueError(msg)
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


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


def _typst_command() -> tuple[list[str], int]:
    """Return the Typst CLI command and timeout: `typst` on PATH, else `mise exec typst`."""
    if typst := shutil.which("typst"):
        return [typst], 60
    if mise := shutil.which("mise"):
        return [mise, "exec", "--quiet", "typst", "--", "typst"], 180
    msg = "Neither `typst` nor `mise` is on PATH; install typst (e.g. `mise install typst`) to compile .typ figures."
    raise RuntimeError(msg)


def _typst_font_args(resolved_root: Path, resolved_typ: Path) -> list[str]:
    """Return repeatable --font-path flags for document-local and user font directories."""
    home = Path.home()
    candidates = (
        resolved_root / "assets" / "fonts",
        resolved_root / "fonts",
        resolved_typ.parent / "assets" / "fonts",
        resolved_typ.parent / "fonts",
        home / ".local" / "share" / "fonts",
        home / "Library" / "Fonts",
    )
    args: list[str] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            args.extend(["--font-path", str(resolved)])
    return args


def render_typst_png(
    typ_path: Path,
    out_png: Path,
    scale: float = 2,
    max_width_px: int | None = None,
    root_dir: Path | None = None,
) -> tuple[int, int]:
    """Compile a single-page Typst figure to PNG, failing on font warnings and capping width when requested."""
    resolved_typ = typ_path.resolve()
    resolved_out = out_png.resolve()
    if resolved_out == resolved_typ:
        msg = f"Output path must differ from source: {out_png}"
        raise ValueError(msg)
    command, timeout = _typst_command()
    resolved_root = (root_dir or resolved_typ.parent).resolve()
    font_args = _typst_font_args(resolved_root, resolved_typ)
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    ppi = 96.0 * scale
    width = 0
    for _ in range(3):
        resolved_out.unlink(missing_ok=True)
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
                *font_args,
                str(resolved_typ),
                str(resolved_out),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        if proc.returncode != 0 or not resolved_out.is_file() or resolved_out.stat().st_size == 0:
            msg = f"typst failed to compile {typ_path.name} (exit {proc.returncode}): {detail}"
            raise RuntimeError(msg)
        if proc.stderr.strip():
            msg = f"typst emitted warnings while compiling {typ_path.name}: {detail}"
            raise RuntimeError(msg)
        width, height = png_size(resolved_out)
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
        # Override locked global mise config so ad-hoc `mise exec` can resolve the pinned Mermaid CLI.
        env = {**os.environ, "MISE_LOCKED": "0", "PUPPETEER_EXECUTABLE_PATH": chrome_bin}
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
