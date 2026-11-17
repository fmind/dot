#!/usr/bin/env python3
"""Validate, compile, export PPTX/PNGs, and safely upload Typst 16:9 slide decks to Drive/Google Slides."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import pptx_builder  # noqa: E402
import slides_drive  # noqa: E402
import typst_check  # noqa: E402

ALLOWED_FIGURE_FORMATS = typst_check.ALLOWED_FIGURE_FORMATS
FOLDER_MIME = slides_drive.FOLDER_MIME
GOOGLE_SLIDES_MIME = slides_drive.GOOGLE_SLIDES_MIME
_collect_typst_warnings = typst_check.collect_typst_warnings
_raise_on_typst_warnings = typst_check.raise_on_typst_warnings
_run_gws = slides_drive.run_gws
_run_typst = typst_check.run_typst
_typst_font_args = typst_check.typst_font_args
build_pptx = pptx_builder.build_pptx
check_typst_prose_with_vale = typst_check.check_typst_prose_with_vale
collect_source_files = typst_check.collect_source_files
collect_typ_files = typst_check.collect_typ_files
discover_font_paths = typst_check.discover_font_paths
inspect_pptx_metadata = pptx_builder.inspect_pptx_metadata
query_deck_info = typst_check.query_deck_info
scan_typst_escaping_issues = typst_check.scan_typst_escaping_issues
upload_deck_artifact = slides_drive.upload_deck_artifact

__all__ = [
    "ALLOWED_FIGURE_FORMATS",
    "FOLDER_MIME",
    "GOOGLE_SLIDES_MIME",
    "_run_gws",
    "_run_typst",
    "build_pptx",
    "collect_source_files",
    "collect_typ_files",
    "discover_font_paths",
    "inspect_pptx_metadata",
    "main",
    "query_deck_info",
    "run_check",
    "run_render",
    "run_upload",
    "scan_typst_escaping_issues",
    "shutil",
    "subprocess",
]


def _emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return
    for key, value in payload.items():
        sys.stdout.write(f"{key}: {value}\n")


def run_render(args: argparse.Namespace) -> dict[str, Any]:
    """Validate escaping, compile a standalone .typ visual card to PNG/SVG, and check font/syntax warnings."""
    source_arg: Path = args.source
    source_path = source_arg.resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".typ":
        raise ValueError(f"Typst source file must be an existing .typ file: {source_arg}")
    if args.format not in ALLOWED_FIGURE_FORMATS:
        raise ValueError(f"--format must be one of {sorted(ALLOWED_FIGURE_FORMATS)}")
    if not 72 <= args.ppi <= 600:
        raise ValueError("--ppi must be between 72 and 600")

    root_dir = (args.root or source_path.parent).resolve()
    if not source_path.is_relative_to(root_dir):
        raise ValueError(f"Typst source must reside inside --root ({root_dir}): {source_path}")
    out_path = (args.output or source_path.with_suffix(f".{args.format}")).resolve()
    if out_path == source_path or out_path.suffix.lower() == ".typ":
        raise ValueError(f"Output path must differ from Typst source files: {args.output or out_path}")

    issues = scan_typst_escaping_issues(source_path.read_text(encoding="utf-8"), label=source_path.name)
    prose_errors, prose_warnings = check_typst_prose_with_vale([source_path], base_dir=root_dir)
    issues.extend(prose_errors)
    if issues:
        if args.json_output:
            sys.stdout.write(json.dumps({"ok": False, "issues": issues}, indent=2) + "\n")
        raise ValueError("; ".join(issues))
    for warning in prose_warnings:
        sys.stderr.write(f"Warning: {warning}\n")

    fonts = discover_font_paths(source_path, args.font_path)
    font_args = _typst_font_args(fonts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["compile", "--root", str(root_dir), *font_args, "--format", args.format]
    if args.format == "png":
        cmd.extend(["--ppi", str(args.ppi)])
    cmd.extend([str(source_path), str(out_path)])
    proc = _run_typst(cmd)
    if proc.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-400:]
        raise RuntimeError(f"Error rendering {source_path.name}: {detail}")

    warnings, syntax_warnings, font_warnings, other_warnings = _collect_typst_warnings(proc.stderr or "")
    strict_fonts = not args.allow_font_warnings
    payload: dict[str, Any] = {
        "ok": not syntax_warnings and not other_warnings and (not font_warnings or not strict_fonts),
        "source": str(source_path),
        "output": str(out_path),
        "format": args.format,
        "ppi": args.ppi if args.format == "png" else None,
        "root": str(root_dir),
        "font_paths": [str(p) for p in fonts],
        "warnings": warnings,
    }
    if prose_warnings:
        payload["prose_warnings"] = prose_warnings
    _emit(payload, json_output=args.json_output)
    _raise_on_typst_warnings(syntax_warnings, font_warnings, other_warnings, strict_fonts=strict_fonts)
    return payload


def run_check(args: argparse.Namespace) -> dict[str, Any]:
    """Validate Typst escaping, compile figures/PDF/PNGs (+ optional .pptx), and check warnings."""
    deck_arg: Path = args.deck
    deck_path = deck_arg.resolve()
    if not deck_path.is_file() or deck_path.suffix.lower() != ".typ":
        raise ValueError(f"Deck source must be an existing .typ file: {deck_arg}")
    if args.figure_format not in ALLOWED_FIGURE_FORMATS:
        raise ValueError(f"--figure-format must be one of {sorted(ALLOWED_FIGURE_FORMATS)}")
    if args.expected_slides is not None and args.expected_slides < 1:
        raise ValueError("--expected-slides must be >= 1")
    if args.max_words is not None and args.max_words < 1:
        raise ValueError("--max-words must be >= 1")
    if not 72 <= args.ppi <= 600:
        raise ValueError("--ppi must be between 72 and 600")

    deck_dir = deck_path.parent
    issues: list[str] = []
    typ_files = collect_typ_files(deck_dir)
    for typ_file in typ_files:
        rel_label = typ_file.relative_to(deck_dir).as_posix()
        issues.extend(scan_typst_escaping_issues(typ_file.read_text(encoding="utf-8"), label=rel_label))
    prose_errors, prose_warnings = check_typst_prose_with_vale(typ_files, base_dir=deck_dir)
    issues.extend(prose_errors)
    if issues:
        if args.json_output:
            sys.stdout.write(json.dumps({"ok": False, "issues": issues}, indent=2) + "\n")
        raise ValueError("; ".join(issues))
    for warning in prose_warnings:
        sys.stderr.write(f"Warning: {warning}\n")

    fonts = discover_font_paths(deck_path, args.font_path)
    font_args = _typst_font_args(fonts)
    strict_fonts = not args.allow_font_warnings

    all_warnings: list[str] = []
    syntax_warnings: list[str] = []
    font_warnings: list[str] = []
    other_warnings: list[str] = []
    rendered_figures: list[str] = []

    if args.render_figures and (figures_dir := deck_dir / "figures").is_dir():
        for fig_src in sorted(figures_dir.glob("*.typ")):
            fig_out = fig_src.with_suffix(f".{args.figure_format}")
            cmd = ["compile", "--root", str(deck_dir), *font_args, "--format", args.figure_format]
            if args.figure_format == "png":
                cmd.extend(["--ppi", str(args.ppi)])
            cmd.extend([str(fig_src), str(fig_out)])
            proc = _run_typst(cmd)
            if proc.returncode != 0:
                detail = " ".join((proc.stderr or proc.stdout).split())[-400:]
                raise RuntimeError(f"Error compiling figure {fig_src.name}: {detail}")
            fw, f_syn, f_font, f_other = _collect_typst_warnings(proc.stderr or "")
            all_warnings.extend(f"{fig_src.name}: {w}" for w in fw)
            syntax_warnings.extend(f"{fig_src.name}: {w}" for w in f_syn)
            font_warnings.extend(f"{fig_src.name}: {w}" for w in f_font)
            other_warnings.extend(f"{fig_src.name}: {w}" for w in f_other)
            rendered_figures.append(str(fig_out))

    pdf_path = (args.output or deck_path.with_suffix(".pdf")).resolve()
    source_typ_paths = {deck_path, *(p.resolve() for p in collect_typ_files(deck_dir))}
    if pdf_path in source_typ_paths or pdf_path.suffix.lower() == ".typ":
        raise ValueError(f"Output PDF path must differ from Typst source files: {args.output or pdf_path}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = (args.png_dir or (deck_dir / "_preview")).resolve()
    preview_dir.mkdir(parents=True, exist_ok=True)
    stem = deck_path.stem
    slide_png_re = re.compile(rf"^{re.escape(stem)}-(\d+)\.png$")
    for stale_png in preview_dir.iterdir():
        if stale_png.is_file() and slide_png_re.match(stale_png.name):
            stale_png.unlink()

    pdf_proc = _run_typst(["compile", "--root", str(deck_dir), *font_args, str(deck_path), str(pdf_path)])
    if pdf_proc.returncode != 0:
        detail = " ".join((pdf_proc.stderr or pdf_proc.stdout).split())[-400:]
        raise RuntimeError(f"Typst PDF compile failed: {detail}")

    png_pattern = preview_dir / f"{stem}-{{p}}.png"
    png_proc = _run_typst(
        [
            "compile",
            "--root",
            str(deck_dir),
            *font_args,
            "--format",
            "png",
            "--ppi",
            str(args.ppi),
            str(deck_path),
            str(png_pattern),
        ]
    )
    if png_proc.returncode != 0:
        detail = " ".join((png_proc.stderr or png_proc.stdout).split())[-400:]
        raise RuntimeError(f"Typst PNG render failed: {detail}")

    png_pairs = [
        (int(match.group(1)), path)
        for path in preview_dir.iterdir()
        if path.is_file() and (match := slide_png_re.match(path.name))
    ]
    png_files = [path for _, path in sorted(png_pairs, key=lambda pair: pair[0])]
    slide_count = len(png_files)
    if slide_count == 0:
        raise RuntimeError(f"Typst produced zero PNG preview slides in {preview_dir}")

    pptx_path: Path | None = None
    notes_slides: list[int] = []
    slide_words: dict[int, int] = {}
    word_violations: dict[int, int] = {}
    if args.pptx is not None or args.max_words is not None:
        notes, meta_title, slide_words = query_deck_info(deck_path, deck_dir, font_args, run_typst_fn=_run_typst)
        if args.max_words is not None:
            if not slide_words:
                raise ValueError(
                    "No <fmind-slide-words> metadata found; import fmind-slides.typ to enforce --max-words."
                )
            word_violations = {page: count for page, count in slide_words.items() if count > args.max_words}
        if args.pptx is not None:
            pptx_target = pdf_path.with_suffix(".pptx") if str(args.pptx) == "__AUTO__" else args.pptx.resolve()
            if pptx_target in source_typ_paths or pptx_target.suffix.lower() == ".typ":
                raise ValueError(f"Output PPTX path must differ from Typst source files: {pptx_target}")
            pptx_path = build_pptx(png_files, pptx_target, title=(meta_title or stem), speaker_notes=notes)
            notes_slides = sorted(notes)

    dw, d_syn, d_font, d_other = _collect_typst_warnings(pdf_proc.stderr or "")
    pw, p_syn, p_font, p_other = _collect_typst_warnings(png_proc.stderr or "")
    all_warnings.extend(dict.fromkeys([*dw, *pw]))
    syntax_warnings.extend(dict.fromkeys([*d_syn, *p_syn]))
    font_warnings.extend(dict.fromkeys([*d_font, *p_font]))
    other_warnings.extend(dict.fromkeys([*d_other, *p_other]))
    overflow = args.expected_slides is not None and slide_count != args.expected_slides

    ok = (
        not overflow
        and not word_violations
        and not syntax_warnings
        and not other_warnings
        and (not font_warnings or not strict_fonts)
    )
    payload: dict[str, Any] = {
        "ok": ok,
        "deck": str(deck_path),
        "pdf": str(pdf_path),
        "slide_count": slide_count,
        "expected_slides": args.expected_slides,
        "png_dir": str(preview_dir),
        "png_files": [str(p) for p in png_files],
        "font_paths": [str(p) for p in fonts],
        "rendered_figures": rendered_figures,
        "warnings": all_warnings,
    }
    if pptx_path is not None:
        payload["pptx"] = str(pptx_path)
        payload["speaker_notes_slides"] = notes_slides
    if slide_words:
        payload["slide_words"] = slide_words
    if args.max_words is not None:
        payload["max_words"] = args.max_words
        payload["word_violations"] = word_violations
    if prose_warnings:
        payload["prose_warnings"] = prose_warnings
    _emit(payload, json_output=args.json_output)

    _raise_on_typst_warnings(syntax_warnings, font_warnings, other_warnings, strict_fonts=strict_fonts)
    if word_violations:
        details = ", ".join(f"slide {page}: {count} words" for page, count in sorted(word_violations.items()))
        raise ValueError(f"Slide word limit exceeded (max {args.max_words}): {details}")
    if overflow:
        raise ValueError(
            f"Overflow/mismatch: expected {args.expected_slides} slides, compiled {slide_count}. "
            f"Inspect {preview_dir} for clipped or spilled content."
        )
    return payload


def run_upload(args: argparse.Namespace) -> dict[str, Any]:
    """Validate .pdf or .pptx bytes, stage in a private tempdir, upload via gws, and verify read-back."""
    result = upload_deck_artifact(args, run_gws_fn=_run_gws)
    _emit(result, json_output=args.json_output)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_p = subparsers.add_parser(
        "check",
        help="Validate Typst escaping, compile figures/PDF/PNGs (+ optional .pptx), and check warnings.",
        allow_abbrev=False,
    )
    check_p.add_argument("deck", type=Path, help="Main Typst deck source (.typ).")
    check_p.add_argument("-o", "--output", type=Path, default=None, help="Compiled PDF output path.")
    check_p.add_argument(
        "--pptx",
        nargs="?",
        const=Path("__AUTO__"),
        default=None,
        type=Path,
        help="Also pack 16:9 PNGs + speaker notes into a .pptx file (default: <pdf_stem>.pptx).",
    )
    check_p.add_argument(
        "--expected-slides", type=int, default=None, help="Fail if rendered page count differs from N."
    )
    check_p.add_argument(
        "--max-words",
        type=int,
        default=None,
        help="Fail if any slide exceeds N visible words reported in <fmind-slide-words>.",
    )
    check_p.add_argument("--png-dir", type=Path, default=None, help="Directory for PNG slide previews.")
    check_p.add_argument("--ppi", type=int, default=192, help="PNG preview resolution (72-600, default: 192).")
    check_p.add_argument("--render-figures", action="store_true", help="Compile figures/*.typ before main deck.")
    check_p.add_argument(
        "--figure-format",
        default="svg",
        choices=sorted(ALLOWED_FIGURE_FORMATS),
        help="Figure output format when --render-figures is set (default: svg).",
    )
    check_p.add_argument(
        "--font-path", type=Path, action="append", default=None, help="Additional Typst font directory."
    )
    check_p.add_argument(
        "--allow-font-warnings",
        action="store_true",
        help="Allow Typst `unknown font family` warnings instead of failing closed.",
    )
    check_p.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")

    upload_p = subparsers.add_parser(
        "upload",
        help="Stage a validated .pdf or .pptx in a private tempdir, upload via gws, and verify read-back.",
        allow_abbrev=False,
    )
    upload_p.add_argument("artifact", type=Path, help="Compiled .pdf or .pptx file to upload to Google Drive.")
    upload_p.add_argument("--drive-folder", default=None, help="Target Google Drive folder ID.")
    upload_p.add_argument("--file-id", default=None, help="Existing Google Drive file ID to update in place.")
    upload_p.add_argument("--name", default=None, help="Remote Drive filename.")
    upload_p.add_argument(
        "--google-slides",
        action="store_true",
        help="Convert uploaded .pptx into a native Google Slides presentation (requires .pptx input).",
    )
    upload_p.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Optional deck directory whose *.typ, figures/*.typ, and *.py sources sync to Drive assets/<slug>/.",
    )
    upload_p.add_argument(
        "--protect-copy",
        action="store_true",
        help="Set copyRequiresWriterPermission=true on the uploaded Drive file.",
    )
    upload_p.add_argument(
        "--dry-run", action="store_true", help="Validate inputs and print plan without modifying Drive."
    )
    upload_p.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")

    render_p = subparsers.add_parser(
        "render",
        help="Validate escaping and compile a standalone .typ visual card or figure to PNG/SVG.",
        allow_abbrev=False,
    )
    render_p.add_argument("source", type=Path, help="Standalone Typst visual card (.typ).")
    render_p.add_argument("-o", "--output", type=Path, default=None, help="Compiled PNG or SVG output path.")
    render_p.add_argument(
        "--format",
        default="png",
        choices=sorted(ALLOWED_FIGURE_FORMATS),
        help="Output image format (default: png).",
    )
    render_p.add_argument("--ppi", type=int, default=192, help="PNG resolution (72-600, default: 192).")
    render_p.add_argument("--root", type=Path, default=None, help="Typst --root directory (default: source parent).")
    render_p.add_argument(
        "--font-path", type=Path, action="append", default=None, help="Additional Typst font directory."
    )
    render_p.add_argument(
        "--allow-font-warnings",
        action="store_true",
        help="Allow Typst `unknown font family` warnings instead of failing closed.",
    )
    render_p.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            run_check(args)
        elif args.command == "render":
            run_render(args)
        else:
            run_upload(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        if getattr(args, "json_output", False):
            sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
