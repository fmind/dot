#!/usr/bin/env python3
"""Compile and export Typst 16:9 slide decks and figure cards to PDF, PNG, SVG, and PPTX."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import pptx_builder  # noqa: E402

__all__ = ["ALLOWED_FIGURE_FORMATS", "discover_font_paths", "main", "run_check", "run_render", "run_typst"]

ALLOWED_FIGURE_FORMATS = frozenset({"svg", "png"})
_AUTO_PPTX = object()


def discover_font_paths(deck_path: Path, extra_paths: list[Path] | None = None) -> list[Path]:
    """Discover existing font directories near the deck, repo root, or standard user font dirs."""
    candidates: list[Path] = list(extra_paths) if extra_paths else []
    deck_dir = deck_path.resolve().parent
    candidates.extend([deck_dir / "assets" / "fonts", deck_dir / "fonts"])
    for parent in deck_dir.parents:
        candidates.append(parent / "assets" / "fonts")
        if (parent / ".git").exists():
            break

    home = Path.home()
    candidates.extend([home / ".local" / "share" / "fonts", home / "Library" / "Fonts"])

    seen: set[Path] = set()
    resolved: list[Path] = []
    for candidate in candidates:
        path = candidate.resolve()
        if path not in seen and path.is_dir():
            seen.add(path)
            resolved.append(path)
    return resolved


def _typst_font_args(font_paths: list[Path]) -> list[str]:
    return [arg for path in font_paths for arg in ("--font-path", str(path))]


def _typst_command() -> tuple[list[str], int]:
    """Return the Typst CLI command and timeout: `typst` on PATH, else `mise exec typst`."""
    if typst := shutil.which("typst"):
        return [typst], 120
    if mise := shutil.which("mise"):
        return [mise, "exec", "--quiet", "typst", "--", "typst"], 180
    msg = "Neither `typst` nor `mise` is on PATH; install typst (e.g. `mise install typst`) before running check."
    raise RuntimeError(msg)


def run_typst(args: list[str]) -> subprocess.CompletedProcess[str]:
    command, timeout = _typst_command()
    return subprocess.run(  # noqa: S603 - fixed CLI command and validated local paths
        [*command, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _query_deck_info(
    deck_path: Path,
    deck_dir: Path,
    font_args: list[str],
    *,
    run_typst_fn: Callable[[list[str]], subprocess.CompletedProcess[str]] = run_typst,
) -> tuple[dict[int, str], str | None, dict[int, int], set[int]]:
    """Extract speaker notes, deck title, per-slide visible word counts, and appendix flags via `typst eval`."""
    expr = (
        "(notes: query(<fmind-speaker-note>).map(it => it.value), "
        "meta: query(<fmind-deck-meta>).map(it => it.value), "
        "words: query(<fmind-slide-words>).map(it => it.value))"
    )
    proc = run_typst_fn(["eval", expr, "--root", str(deck_dir), *font_args, "--in", str(deck_path), "--format", "json"])
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        raise RuntimeError(f"Typst metadata query failed: {detail}")
    raw = proc.stdout.strip()
    payload = json.loads(raw) if raw else {}
    notes_by_page: dict[int, list[str]] = {}
    deck_title: str | None = None
    words_by_page: dict[int, int] = {}
    appendix_pages: set[int] = set()
    if isinstance(payload, dict):
        for entry in payload.get("notes") or []:
            if isinstance(entry, dict) and isinstance(entry.get("page"), int) and isinstance(entry.get("note"), str):
                text = entry["note"].strip()
                if text:
                    notes_by_page.setdefault(entry["page"], []).append(text)
        for entry in payload.get("meta") or []:
            if isinstance(entry, dict) and isinstance(entry.get("title"), str):
                candidate = entry["title"].strip()
                if candidate:
                    deck_title = candidate
        for entry in payload.get("words") or []:
            if isinstance(entry, dict) and isinstance(entry.get("page"), int) and isinstance(entry.get("words"), int):
                words_by_page[entry["page"]] = entry["words"]
                if entry.get("appendix") is True:
                    appendix_pages.add(entry["page"])
    notes = {page: "\n\n".join(parts) for page, parts in sorted(notes_by_page.items())}
    return notes, deck_title, dict(sorted(words_by_page.items())), appendix_pages


def _collect_typst_warnings(stderr: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Split Typst warning lines into `(all_warnings, syntax_warnings, font_warnings, other_warnings)`."""
    warnings = [line for line in stderr.splitlines() if "warning:" in line.lower()]
    syntax_warnings: list[str] = []
    font_warnings: list[str] = []
    other_warnings: list[str] = []
    for warning in warnings:
        lowered = warning.lower()
        if "no text within stars" in lowered:
            syntax_warnings.append(warning)
        elif "unknown font family" in lowered:
            font_warnings.append(warning)
        else:
            other_warnings.append(warning)
    return warnings, syntax_warnings, font_warnings, other_warnings


def _raise_on_typst_warnings(
    syntax_warnings: list[str],
    font_warnings: list[str],
    other_warnings: list[str],
    *,
    strict_fonts: bool,
) -> None:
    if syntax_warnings:
        raise ValueError("Typst markup warning: found empty bold stars (`**...**`). Typst uses single `*bold*`.")
    if font_warnings and strict_fonts:
        msg = (
            "Typst font warning: missing required font family ("
            + "; ".join(font_warnings)
            + "). Pass --font-path or install the theme fonts (or use --allow-font-warnings explicitly)."
        )
        raise RuntimeError(msg)
    if other_warnings:
        raise RuntimeError("Typst emitted unexpected warnings: " + "; ".join(other_warnings))


def _collect_typ_files(deck_dir: Path) -> list[Path]:
    files = sorted(p for p in deck_dir.glob("*.typ") if p.is_file())
    figures_dir = deck_dir / "figures"
    if figures_dir.is_dir():
        files.extend(sorted(p for p in figures_dir.glob("*.typ") if p.is_file()))
    return files


def _emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return
    for key, value in payload.items():
        sys.stdout.write(f"{key}: {value}\n")


def run_render(args: argparse.Namespace, *, state: dict[str, bool] | None = None) -> dict[str, Any]:
    """Compile a standalone .typ visual card to PNG/SVG and fail closed on warnings."""
    source_arg: Path = args.source
    source_path = source_arg.resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".typ":
        raise ValueError(f"Typst source file must be an existing .typ file: {source_arg}")
    if args.format not in ALLOWED_FIGURE_FORMATS:
        raise ValueError(f"--format must be one of {sorted(ALLOWED_FIGURE_FORMATS)}")
    if not 72 <= args.ppi <= 600:
        raise ValueError("--ppi must be between 72 and 600")

    if args.root is not None:
        root_dir = args.root.resolve()
    elif source_path.parent.name == "figures" and (source_path.parent.parent / "fmind-slides.typ").is_file():
        root_dir = source_path.parent.parent
    else:
        root_dir = source_path.parent
    if not source_path.is_relative_to(root_dir):
        raise ValueError(f"Typst source must reside inside --root ({root_dir}): {source_path}")
    out_path = (args.output or source_path.with_suffix(f".{args.format}")).resolve()
    if out_path == source_path or out_path.suffix.lower() == ".typ":
        raise ValueError(f"Output path must differ from Typst source files: {args.output or out_path}")

    extra_fonts = list(args.font_path) if args.font_path else []
    if root_dir != source_path.parent and (root_dir / "fonts").is_dir():
        extra_fonts.append(root_dir / "fonts")
    fonts = discover_font_paths(source_path, extra_fonts or None)
    font_args = _typst_font_args(fonts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["compile", "--root", str(root_dir), *font_args, "--format", args.format]
    if args.format == "png":
        cmd.extend(["--ppi", str(args.ppi)])
    cmd.extend([str(source_path), str(out_path)])
    proc = run_typst(cmd)
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
    _emit(payload, json_output=args.json_output)
    if state is not None:
        state["emitted_json"] = bool(args.json_output)
    _raise_on_typst_warnings(syntax_warnings, font_warnings, other_warnings, strict_fonts=strict_fonts)
    return payload


def run_check(args: argparse.Namespace, *, state: dict[str, bool] | None = None) -> dict[str, Any]:
    """Compile figures/PDF/PNGs (+ optional .pptx) and enforce slide-count, word-cap, and warning gates."""
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
    typ_files = _collect_typ_files(deck_dir)
    fonts = discover_font_paths(deck_path, args.font_path)
    font_args = _typst_font_args(fonts)
    strict_fonts = not args.allow_font_warnings

    all_warnings: list[str] = []
    syntax_warnings: list[str] = []
    font_warnings: list[str] = []
    other_warnings: list[str] = []
    rendered_figures: list[str] = []

    if args.render_figures:
        figures_dir = deck_dir / "figures"
        fig_sources = sorted(p for p in figures_dir.glob("*.typ") if p.is_file()) if figures_dir.is_dir() else []
        if not fig_sources:
            raise ValueError(f"--render-figures specified, but no figures/*.typ files found under {deck_dir}")
        for fig_src in fig_sources:
            fig_out = fig_src.with_suffix(f".{args.figure_format}")
            cmd = ["compile", "--root", str(deck_dir), *font_args, "--format", args.figure_format]
            if args.figure_format == "png":
                cmd.extend(["--ppi", str(args.ppi)])
            cmd.extend([str(fig_src), str(fig_out)])
            proc = run_typst(cmd)
            if proc.returncode != 0 or not fig_out.is_file() or fig_out.stat().st_size == 0:
                detail = " ".join((proc.stderr or proc.stdout).split())[-400:]
                raise RuntimeError(f"Error compiling figure {fig_src.name}: {detail or 'output missing or empty'}")
            fw, f_syn, f_font, f_other = _collect_typst_warnings(proc.stderr or "")
            all_warnings.extend(f"{fig_src.name}: {w}" for w in fw)
            syntax_warnings.extend(f"{fig_src.name}: {w}" for w in f_syn)
            font_warnings.extend(f"{fig_src.name}: {w}" for w in f_font)
            other_warnings.extend(f"{fig_src.name}: {w}" for w in f_other)
            rendered_figures.append(str(fig_out))

    pdf_path = (args.output or deck_path.with_suffix(".pdf")).resolve()
    source_typ_paths = {deck_path, *(p.resolve() for p in typ_files)}
    if pdf_path in source_typ_paths or pdf_path.suffix.lower() == ".typ":
        raise ValueError(f"Output PDF path must differ from Typst source files: {args.output or pdf_path}")
    pptx_target: Path | None = None
    if args.pptx is not None:
        pptx_target = pdf_path.with_suffix(".pptx") if args.pptx is _AUTO_PPTX else args.pptx.resolve()
        if pptx_target in source_typ_paths or pptx_target.suffix.lower() == ".typ":
            raise ValueError(f"Output PPTX path must differ from Typst source files: {pptx_target}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = (args.png_dir or (deck_dir / "_preview")).resolve()
    preview_dir.mkdir(parents=True, exist_ok=True)
    stem = deck_path.stem
    slide_png_re = re.compile(rf"^{re.escape(stem)}-(\d+)\.png$")
    for stale_png in preview_dir.iterdir():
        if stale_png.is_file() and slide_png_re.match(stale_png.name):
            stale_png.unlink()

    pdf_proc = run_typst(["compile", "--root", str(deck_dir), *font_args, str(deck_path), str(pdf_path)])
    if pdf_proc.returncode != 0:
        detail = " ".join((pdf_proc.stderr or pdf_proc.stdout).split())[-400:]
        raise RuntimeError(f"Typst PDF compile failed: {detail}")

    png_pattern = preview_dir / f"{stem}-{{p}}.png"
    png_proc = run_typst(
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
    notes: dict[int, str] = {}
    meta_title: str | None = None
    notes_slides: list[int] = []
    slide_words: dict[int, int] = {}
    appendix_slides: set[int] = set()
    word_violations: dict[int, int] = {}
    if pptx_target is not None or args.max_words is not None:
        notes, meta_title, slide_words, appendix_slides = _query_deck_info(
            deck_path, deck_dir, font_args, run_typst_fn=run_typst
        )
        if args.max_words is not None:
            if not slide_words:
                raise ValueError(
                    "No <fmind-slide-words> metadata found; import fmind-slides.typ to enforce --max-words."
                )
            word_violations = {
                page: count
                for page, count in slide_words.items()
                if count > args.max_words and page not in appendix_slides
            }

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
    if ok and pptx_target is not None:
        pptx_path = pptx_builder.build_pptx(
            png_files,
            pptx_target,
            title=(meta_title or stem),
            speaker_notes=notes,
            lang=getattr(args, "lang", "en-US"),
            theme_name=getattr(args, "theme_name", "Fmind"),
        )
        notes_slides = sorted(notes)
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
    if appendix_slides:
        payload["appendix_slides"] = sorted(appendix_slides)
    if args.max_words is not None:
        payload["max_words"] = args.max_words
        payload["word_violations"] = word_violations
    _emit(payload, json_output=args.json_output)
    if state is not None:
        state["emitted_json"] = bool(args.json_output)

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_p = subparsers.add_parser(
        "check",
        help="Compile figures/PDF/PNGs (+ optional .pptx) and enforce slide-count, word-cap, and warning gates.",
        allow_abbrev=False,
    )
    check_p.add_argument("deck", type=Path, help="Main Typst deck source (.typ).")
    check_p.add_argument("-o", "--output", type=Path, default=None, help="Compiled PDF output path.")
    check_p.add_argument(
        "--pptx",
        nargs="?",
        const=_AUTO_PPTX,
        default=None,
        type=Path,
        help="Also pack 16:9 PNGs + speaker notes into a .pptx file (default: <pdf_stem>.pptx).",
    )
    check_p.add_argument(
        "--lang",
        default="en-US",
        help="BCP-47 language tag for PPTX speaker notes XML (default: en-US; for example, fr-FR).",
    )
    check_p.add_argument(
        "--theme-name",
        default="Fmind",
        help="PPTX theme name (default: Fmind; pass 'neutral' for unbranded customer decks).",
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

    render_p = subparsers.add_parser(
        "render",
        help="Compile a standalone .typ visual card or figure to PNG/SVG.",
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
    state = {"emitted_json": False}
    try:
        if args.command == "check":
            run_check(args, state=state)
        else:
            run_render(args, state=state)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        if getattr(args, "json_output", False):
            err_payload = json.dumps({"ok": False, "error": str(exc)}) + "\n"
            if not state["emitted_json"]:
                sys.stdout.write(err_payload)
            sys.stderr.write(err_payload)
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
