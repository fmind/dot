"""Compile and validate Google Docs native Markdown (.md) with Typst, Mermaid, and SVG figures."""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Re-export drive and renderer symbols so callers and tests can import or monkeypatch them on this module.
from docs_drive import ASSET_MIME_TYPES as ASSET_MIME_TYPES  # noqa: E402
from docs_drive import DOC_SLUG_RE as DOC_SLUG_RE  # noqa: E402
from docs_drive import DRIVE_ID_RE as DRIVE_ID_RE  # noqa: E402
from docs_drive import prepare_drive_context  # noqa: E402
from docs_drive import run_gws as run_gws  # noqa: E402
from docs_drive import upload_to_drive as _drive_upload_to_drive  # noqa: E402
from figure_render import MAX_FIGURE_WIDTH_PX as MAX_FIGURE_WIDTH_PX  # noqa: E402
from figure_render import MERMAID_CLI as MERMAID_CLI  # noqa: E402
from figure_render import SVG_CANVAS_WIDTH as SVG_CANVAS_WIDTH  # noqa: E402
from figure_render import SVG_CHECKER as SVG_CHECKER  # noqa: E402
from figure_render import check_svg as check_svg  # noqa: E402
from figure_render import png_size as png_size  # noqa: E402
from figure_render import render_mermaid_png as render_mermaid_png  # noqa: E402
from figure_render import render_svg_png as render_svg_png  # noqa: E402
from figure_render import render_typst_png as render_typst_png  # noqa: E402
from figure_render import svg_checker as svg_checker  # noqa: E402

MAX_SCALE = 4
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
NON_LOCAL_PREFIXES = ("http://", "https://", "data:")  # image links the compiler does not read from disk
MERMAID_ALT_RE = re.compile(r"^\s*%%\s*alt\s*:\s*(.+?)\s*$", re.MULTILINE)
CAPTION_LINE_RE = re.compile(r"^\s*(?:\*([^*\r\n]+)\*|_([^_\r\n]+)_)\s*$")
INLINE_CODE_RE = re.compile(r"`[^`\r\n]+`")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")


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
    """Upload compiled .md and assets/<doc-slug>/ bundle via the active `run_gws` binding."""
    return _drive_upload_to_drive(
        compiled_md,
        asset_paths,
        gws_dir=gws_dir,
        drive_folder=drive_folder,
        file_id=file_id,
        doc_name=doc_name,
        doc_slug=doc_slug,
        existing_file=existing_file,
        run_gws_fn=run_gws,
    )


def _clean_alt(text: str) -> str:
    """Flatten Markdown links and replace remaining square brackets so `![alt][id]` stays valid."""
    return MD_LINK_RE.sub(r"\1", text).replace("[", "(").replace("]", ")").strip()


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
    if html_match := RAW_HTML_RE.search(outside_code):
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
    for ext, pattern, label in ((".svg", SVG_IMAGE_RE, "SVG images"), (".typ", TYP_IMAGE_RE, "Typst sources")):
        links = [match.group(2) for match in pattern.finditer(outside_code)]
        if any(link.startswith(NON_LOCAL_PREFIXES) for link in links):
            problems.append(
                f"Remote {ext} image link found; remote {label} are unsupported: download the file next to the "
                "document and link it by its local path, or use a PNG instead."
            )
        if any(not link.startswith(NON_LOCAL_PREFIXES) for link in links):
            problems.append(
                f"Uncompiled {ext} image link found; compile it to a Base64 PNG reference with compile_markdown_doc.py."
            )
    return problems


def _encode_figure(
    ref_definitions: list[str], fig_id: str, kind: str, alt_text: str, png_path: Path, source_rel: str | None = None
) -> dict[str, Any]:
    """Encode PNG into Base64 Markdown reference definition and return figure metadata."""
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    ref_definitions.append(f"[{fig_id}]: <data:image/png;base64,{b64}>")
    entry: dict[str, Any] = {"id": fig_id, "kind": kind, "alt": alt_text, "bytes": png_path.stat().st_size}
    if source_rel is not None:
        entry["source"] = source_rel
    return entry


def _copy_figure_assets(
    entry: dict[str, Any],
    assets_dir: Path | None,
    png_path: Path,
    resolved_base: Path,
    claimed: set[str],
    source: str | Path,
) -> None:
    """Copy figure source (.mmd/.svg/.typ), rendered PNG, and any imported fmind.typ into assets_dir."""
    if assets_dir is None:
        return
    png_asset = assets_dir / f"{entry['id']}.png"
    shutil.copy2(png_path, png_asset)
    if isinstance(source, str):
        src_asset = assets_dir / f"{entry['id']}.mmd"
        src_asset.write_text(source.strip() + "\n", encoding="utf-8")
    else:
        # Prefix only a name already taken by another figure in this run; a previous run's copy is overwritten.
        src_asset = assets_dir / source.name
        if src_asset.name in claimed and src_asset.resolve() != source.resolve():
            src_asset = assets_dir / f"{entry['id']}-{source.name}"
        claimed.add(src_asset.name)
        if src_asset.resolve() != source.resolve():
            shutil.copy2(source, src_asset)
        if (
            entry["kind"] == "typst"
            and (theme := source.parent / "fmind.typ").is_file()
            and (resolved_theme := theme.resolve()).is_relative_to(resolved_base)
            and "fmind.typ" in source.read_text(encoding="utf-8")
        ):
            theme_asset = assets_dir / "fmind.typ"
            if theme_asset.resolve() != resolved_theme:
                shutil.copy2(resolved_theme, theme_asset)
            claimed.add(theme_asset.name)
            entry["companion_assets"] = [str(theme_asset)]
    entry["source_asset"], entry["png_asset"] = str(src_asset), str(png_asset)


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
    resolved_base = base_dir.resolve()
    claimed: set[str] = set()
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
            raw_code = match.group(3)
            alt_match = MERMAID_ALT_RE.search(raw_code)
            cap = CAPTION_LINE_RE.match((source_text[match.end() :].lstrip("\r\n").splitlines() or [""])[0])
            fig_id = next_fig_id()
            raw_alt = alt_match.group(1) if alt_match else (cap.group(1) or cap.group(2) or "" if cap else "")
            alt_text = _clean_alt(raw_alt) or f"Figure {fig_counter}: Architecture diagram"
            png_path = tmp_dir / f"{fig_id}.png"
            render_mermaid_png(raw_code, png_path, scale=scale, max_width_px=MAX_FIGURE_WIDTH_PX)
            entry = _encode_figure(ref_definitions, fig_id, "mermaid", alt_text, png_path)
            _copy_figure_assets(entry, assets_dir, png_path, resolved_base, claimed, raw_code)
            figures.append(entry)
            pieces.extend((source_text[last_idx : match.start()], f"![{alt_text}][{fig_id}]"))
            last_idx = match.end()

        intermediate = "".join([*pieces, source_text[last_idx:]])
        code_spans = [
            *(m.span() for m in FENCED_BLOCK_RE.finditer(intermediate)),
            *(m.span() for m in INLINE_CODE_RE.finditer(intermediate)),
        ]
        fig_pieces: list[str] = []
        last_fig_idx = 0
        for match in LOCAL_FIGURE_RE.finditer(intermediate):
            if any(start <= match.start() < end for start, end in code_spans):
                continue
            fig_rel = match.group(2)
            if fig_rel.startswith(NON_LOCAL_PREFIXES):
                continue  # the dialect check below rejects it as unsupported
            fig_path = (base_dir / fig_rel).resolve()
            is_typ = fig_path.suffix.lower() == ".typ"
            if not fig_path.is_relative_to(resolved_base):
                raise ValueError(f"{'Typst' if is_typ else 'SVG'} path escapes document directory: {fig_rel}")
            if is_typ:
                if not fig_path.is_file():
                    raise ValueError(f"{fig_path}: Typst file not found")
            elif svg_problems := check_svg(fig_path, expected_width=svg_width):
                raise ValueError("; ".join(svg_problems))

            fig_id = next_fig_id()
            alt_text = _clean_alt(match.group(1)) or f"Figure {fig_counter}"
            png_path = tmp_dir / f"{fig_id}.png"
            if is_typ:
                render_typst_png(
                    fig_path, png_path, scale=scale, max_width_px=MAX_FIGURE_WIDTH_PX, root_dir=resolved_base
                )
            else:
                render_svg_png(fig_path, png_path, scale=scale, max_width_px=MAX_FIGURE_WIDTH_PX)
            entry = _encode_figure(ref_definitions, fig_id, "typst" if is_typ else "svg", alt_text, png_path, fig_rel)
            _copy_figure_assets(entry, assets_dir, png_path, resolved_base, claimed, fig_path)
            figures.append(entry)
            fig_pieces.extend((intermediate[last_fig_idx : match.start()], f"![{alt_text}][{fig_id}]"))
            last_fig_idx = match.end()

        compiled = "".join([*fig_pieces, intermediate[last_fig_idx:]]).rstrip() + "\n"

    if ref_definitions:
        compiled = compiled + "\n" + "\n".join(ref_definitions) + "\n"
    if problems := check_markdown_dialect(compiled):
        raise ValueError("; ".join(problems))
    return compiled, figures


def _scale(value: str) -> int:
    """Parse --scale as an integer from 1 to MAX_SCALE; larger factors only bloat the Base64 payload."""
    try:
        scale = int(value)
    except ValueError:
        scale = 0
    if not 1 <= scale <= MAX_SCALE:
        raise argparse.ArgumentTypeError(f"must be an integer from 1 to {MAX_SCALE}, got {value!r}")
    return scale


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("source", type=Path, help="Input .src.md/.md doc or .typ/.svg figure to validate/compile.")
    parser.add_argument("-o", "--output", type=Path, help="Output path (.md for Markdown or .png for Typst/SVG).")
    parser.add_argument("--assets-dir", type=Path, help="Export dir for editable sources and .png figures.")
    parser.add_argument("--drive-folder", type=str, help="Drive folder ID for compiled .md and assets/<doc-slug>/.")
    parser.add_argument("--file-id", type=str, help="Existing Drive .md file ID to update in place.")
    parser.add_argument("--doc-name", type=str, help="Target filename in Google Drive (e.g. 'Review.md').")
    parser.add_argument("--doc-slug", type=str, help="Subfolder slug under assets/<doc-slug>/ in Drive.")
    parser.add_argument("--check-only", action="store_true", help="Validate dialect, SVG, or Typst without output.")
    parser.add_argument("-s", "--scale", type=_scale, default=2, help=f"PNG scale factor 1-{MAX_SCALE} (default: 2).")
    parser.add_argument(
        "--svg-width", type=float, default=SVG_CANVAS_WIDTH, help=f"SVG px ({SVG_CANVAS_WIDTH:g}, 0=off)."
    )
    parser.add_argument("-j", "--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")
    return parser


def _collect_exported_assets(assets_dir: Path, source: Path, figures: list[dict[str, Any]]) -> list[str]:
    """Copy source Markdown into assets_dir and return deduplicated exported asset paths."""
    src_asset = assets_dir / source.name
    if src_asset.resolve() != source.resolve():
        shutil.copy2(source, src_asset)
    paths = [str(src_asset)]
    for fig in figures:
        paths.extend(fig.get("companion_assets", []))
        paths.extend(fig[k] for k in ("source_asset", "png_asset") if fig.get(k))
    return list(dict.fromkeys(paths))


def _resolve_vale_config(cwd: Path | None = None) -> Path | None:
    """Return the nearest project .vale.ini or the global ~/.config/vale/.vale.ini if present."""
    start = (cwd or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        candidate = parent / ".vale.ini"
        if candidate.is_file():
            return candidate
    global_cfg = Path.home() / ".config/vale/.vale.ini"
    return global_cfg if global_cfg.is_file() else None


def check_prose_with_vale(
    text: str,
    *,
    ext: str = ".md",
    label: str = "document.md",
    cwd: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Run Vale prose checks on text when Vale and a config file are available, returning (errors, warnings)."""
    vale_bin = shutil.which("vale")
    if not vale_bin:
        return [], []
    config = _resolve_vale_config(cwd)
    if config is None:
        return [], []
    proc = subprocess.run(  # noqa: S603 - fixed Vale binary and resolved config path
        [vale_bin, "--no-global", "--config", str(config), "--output=JSON", f"--ext={ext}"],
        input=text,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode not in {0, 1}:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"vale failed on {label}: {detail}")
    raw = proc.stdout.strip()
    if not raw:
        return [], []
    data = json.loads(raw)
    errors: list[str] = []
    warnings: list[str] = []
    for findings in data.values():
        for item in findings:
            line = item.get("Line", 1)
            check = item.get("Check", "Vale")
            message = item.get("Message", "")
            match = str(item.get("Match") or "").strip()
            suffix = f" ({match})" if match and match not in message and len(match) <= 40 else ""
            formatted = f"{label}:{line}: [{check}] {message}{suffix}"
            if item.get("Severity") == "error":
                errors.append(formatted)
            else:
                warnings.append(formatted)
    return errors, warnings


def _compile_markdown_cli(args: argparse.Namespace, source: Path) -> dict[str, Any]:
    """Run check-only validation or full Markdown compilation and optional Drive upload."""
    text = source.read_text(encoding="utf-8")
    if args.check_only:
        if problems := check_markdown_dialect(text):
            raise ValueError("; ".join(problems))
        prose_errors, prose_warnings = check_prose_with_vale(text, ext=".md", label=source.name, cwd=source.parent)
        if prose_errors:
            raise ValueError("; ".join(prose_errors))
        for warning in prose_warnings:
            sys.stderr.write((json.dumps({"warning": warning}) if args.json_output else f"Warning: {warning}") + "\n")
        payload: dict[str, Any] = {"status": "ok", "source": str(source), "figures": []}
        if prose_warnings:
            payload["proseWarnings"] = prose_warnings
        return payload

    prose_errors, prose_warnings = check_prose_with_vale(text, ext=".md", label=source.name, cwd=source.parent)
    if prose_errors:
        raise ValueError("; ".join(prose_errors))
    for warning in prose_warnings:
        sys.stderr.write((json.dumps({"warning": warning}) if args.json_output else f"Warning: {warning}") + "\n")

    out_path = args.output or source.with_name(
        source.name.removesuffix(".src.md") + ".md" if source.name.endswith(".src.md") else f"{source.stem}.gdoc.md"
    )
    if out_path.resolve() == source.resolve():
        raise ValueError(f"Output path must differ from source: {out_path}")

    assets_dir: Path | None = args.assets_dir
    # One private directory for every gws call of this run: see upload_to_drive.
    with tempfile.TemporaryDirectory(prefix="draft-doc-") as tmp:
        gws_dir = Path(tmp)
        args.doc_name, doc_slug, existing_file = prepare_drive_context(
            out_path.name, gws_dir, args.drive_folder, args.file_id, args.doc_name, args.doc_slug, run_gws_fn=run_gws
        )
        if (args.drive_folder or args.file_id) and assets_dir is None:
            assets_dir = out_path.parent / "assets" / doc_slug
        compiled, figures = compile_markdown(
            text, source.parent, scale=args.scale, svg_width=args.svg_width, assets_dir=assets_dir
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(compiled, encoding="utf-8")
        exported_assets = _collect_exported_assets(assets_dir, source, figures) if assets_dir is not None else []
        drive_info: dict[str, Any] | None = None
        if args.drive_folder or args.file_id:
            drive_info = upload_to_drive(
                out_path,
                [Path(p) for p in exported_assets],
                gws_dir=gws_dir,
                drive_folder=args.drive_folder,
                file_id=args.file_id,
                doc_name=args.doc_name,
                doc_slug=doc_slug,
                existing_file=existing_file,
            )
            if warning := drive_info["warning"]:
                sys.stderr.write(
                    (json.dumps({"warning": warning}) if args.json_output else f"Warning: {warning}") + "\n"
                )
    result: dict[str, Any] = {
        "status": "ok",
        "source": str(source),
        "output": str(out_path),
        "bytes": len(compiled.encode("utf-8")),
        "figures": figures,
        "assets_dir": str(assets_dir) if assets_dir is not None else None,
        "assets": exported_assets,
        "drive": drive_info,
    }
    if prose_warnings:
        result["proseWarnings"] = prose_warnings
    return result


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, dispatch validation/compilation, and format stdout/stderr output."""
    args = _build_parser().parse_args(argv)
    source: Path = args.source
    output: Path | None = args.output
    try:
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source}")
        if output is not None and output.resolve() == source.resolve():
            raise ValueError(f"Output path must differ from source: {output}")

        suffix = source.suffix.lower()
        if suffix in {".svg", ".typ"}:
            if suffix == ".svg":
                if problems := check_svg(source, expected_width=args.svg_width):
                    raise ValueError("; ".join(problems))
                size = render_svg_png(source, output, scale=args.scale) if (not args.check_only and output) else None
            elif args.check_only or output is None:
                with tempfile.TemporaryDirectory(prefix=".typ-check-") as tmp:
                    size = render_typst_png(source, Path(tmp) / "check.png", scale=args.scale)
            else:
                size = render_typst_png(source, output, scale=args.scale)
            out_val = str(output) if (output is not None and not args.check_only) else None
            payload: dict[str, Any] = {
                "status": "ok",
                "source": str(source),
                "output": out_val,
                "dimensions_px": list(size) if size else None,
            }
        else:
            payload = _compile_markdown_cli(args, source)

        msg = (
            json.dumps(payload, indent=2)
            if args.json_output
            else f"OK {source} -> {payload.get('output') or 'validated'}"
        )
        sys.stdout.write(msg + "\n")
    # Expected failures print one line; anything else is a bug and keeps its traceback.
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        err = json.dumps({"error": str(exc)}) if args.json_output else f"Error: {exc}"
        sys.stderr.write(err + "\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
