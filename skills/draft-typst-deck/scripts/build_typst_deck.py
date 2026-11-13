#!/usr/bin/env python3
"""Validate, compile, preview, and safely upload Typst 16:9 PDF slide decks to Google Drive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")
FORBIDDEN_RAW_ESCAPE_RE = re.compile(r"\\[$~*]")
ODD_STRING_ESCAPE_RE = re.compile(r"(?<!\\)(?:\\\\)*\\([$~*])")
ALLOWED_FIGURE_FORMATS = frozenset({"svg", "png"})


def scan_typst_escaping_issues(source: str, label: str = "<deck>") -> list[str]:
    """Flag backslash escapes ($, ~, *) inside Typst string literals or inline raw spans."""
    issues: list[str] = []
    n = len(source)
    i = 0
    line = 1

    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            i += 1
            continue

        # Skip Typst line comments (// ...)
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            end = source.find("\n", i + 2)
            if end == -1:
                break
            i = end
            continue

        # Skip Typst block comments (/* ... */, supports nesting)
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            depth = 1
            i += 2
            while i < n and depth > 0:
                if source[i] == "\n":
                    line += 1
                elif source[i : i + 2] == "/*":
                    depth += 1
                    i += 2
                    continue
                elif source[i : i + 2] == "*/":
                    depth -= 1
                    i += 2
                    continue
                i += 1
            continue

        # Raw code spans (`...` or ```...```)
        if ch == "`":
            tick_count = 1
            while i + tick_count < n and source[i + tick_count] == "`":
                tick_count += 1
            start_line = line
            i += tick_count
            body_start = i
            fence = "`" * tick_count
            close_idx = source.find(fence, i)
            if close_idx == -1:
                break
            body = source[body_start:close_idx]
            if tick_count == 1:
                issues.extend(
                    f"{label}:{start_line}: remove backslash in inline raw span `{match.group(0)}`; "
                    "Typst renders literal backslashes inside backticks."
                    for match in FORBIDDEN_RAW_ESCAPE_RE.finditer(body)
                )
            line += body.count("\n")
            i = close_idx + tick_count
            continue

        # Double-quoted string literals ("...")
        if ch == '"':
            start_line = line
            i += 1
            chars: list[str] = []
            while i < n:
                curr = source[i]
                if curr == "\\" and i + 1 < n:
                    chars.append(curr)
                    nxt = source[i + 1]
                    if nxt == "\n":
                        line += 1
                    chars.append(nxt)
                    i += 2
                    continue
                if curr == '"':
                    i += 1
                    break
                if curr == "\n":
                    line += 1
                chars.append(curr)
                i += 1
            body = "".join(chars)
            for match in ODD_STRING_ESCAPE_RE.finditer(body):
                token = match.group(1)
                issues.append(
                    f"{label}:{start_line}: unexpected '\\{token}' inside string literal; "
                    f"use unescaped '{token}' inside quotes (only escape inside [...] content blocks)."
                )
            continue

        i += 1

    return issues


def discover_font_paths(deck_path: Path, extra_paths: list[Path] | None = None) -> list[Path]:
    """Discover existing font directories near the deck, repo root, or standard user font dirs."""
    candidates: list[Path] = []
    if extra_paths:
        candidates.extend(extra_paths)
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


def collect_typ_files(deck_dir: Path) -> list[Path]:
    """Collect deck-root and figures .typ files for static validation."""
    files = sorted(p for p in deck_dir.glob("*.typ") if p.is_file())
    figures_dir = deck_dir / "figures"
    if figures_dir.is_dir():
        files.extend(sorted(p for p in figures_dir.glob("*.typ") if p.is_file()))
    return files


def _typst_font_args(font_paths: list[Path]) -> list[str]:
    args: list[str] = []
    for path in font_paths:
        args.extend(["--font-path", str(path)])
    return args


def _typst_command() -> tuple[list[str], int]:
    """Return the Typst CLI command and timeout: `typst` on PATH, else `mise exec typst`."""
    if typst := shutil.which("typst"):
        return [typst], 120
    if mise := shutil.which("mise"):
        return [mise, "exec", "--quiet", "typst", "--", "typst"], 180
    msg = "Neither `typst` nor `mise` is on PATH; install typst (e.g. `mise install typst`) before running check."
    raise RuntimeError(msg)


def _run_typst(args: list[str]) -> subprocess.CompletedProcess[str]:
    command, timeout = _typst_command()
    return subprocess.run(  # noqa: S603 - fixed CLI command and validated local paths
        [*command, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _validate_drive_id(value: str, label: str) -> str:
    cleaned = value.strip()
    if not DRIVE_ID_RE.fullmatch(cleaned):
        msg = f"Invalid Google Drive {label}: {value!r}"
        raise ValueError(msg)
    return cleaned


def _validate_upload_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        msg = f"Remote filename must be a plain filename without path separators: {value!r}"
        raise ValueError(msg)
    return cleaned


def _escape_drive_q(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _run_gws(args: list[str], *, cwd: Path) -> dict[str, Any]:
    gws_bin = shutil.which("gws")
    if not gws_bin:
        msg = "gws CLI not found on PATH; install and authenticate `gws` before uploading."
        raise RuntimeError(msg)
    proc = subprocess.run(  # noqa: S603 - fixed gws CLI binary and structured arguments
        [gws_bin, *args, "--format", "json"],
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        msg = f"gws {' '.join(args[:3])} failed (exit {proc.returncode}): {detail}"
        raise RuntimeError(msg)
    out = proc.stdout.strip()
    if out and not out.startswith(("{", "[")):
        indices = [idx for idx in (out.find("{"), out.find("[")) if idx != -1]
        if indices:
            out = out[min(indices) :]
    data = json.loads(out) if out else {}
    if isinstance(data, dict) and "error" in data:
        msg = f"Google API error: {data['error']}"
        raise RuntimeError(msg)
    return data if isinstance(data, dict) else {"data": data}


def _find_existing_file_in_folder(parent_id: str, name: str, *, cwd: Path) -> str | None:
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    query = (
        "trashed = false and mimeType != 'application/vnd.google-apps.folder' "
        f"and '{valid_parent}' in parents and name = '{_escape_drive_q(name)}'"
    )
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": query,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    while True:
        resp = _run_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=cwd)
        files = resp.get("files") or []
        if files:
            return str(files[0]["id"])
        token = resp.get("nextPageToken")
        if not token:
            return None
        params["pageToken"] = token


def _file_md5_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.md5(usedforsecurity=False)
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return
    for key, value in payload.items():
        sys.stdout.write(f"{key}: {value}\n")


def run_check(args: argparse.Namespace) -> dict[str, Any]:
    """Validate Typst escaping, compile figures and PDF/PNGs, and enforce slide count + warning gates."""
    deck_arg: Path = args.deck
    deck_path = deck_arg.resolve()
    if not deck_path.is_file() or deck_path.suffix.lower() != ".typ":
        msg = f"Deck source must be an existing .typ file: {deck_arg}"
        raise ValueError(msg)
    if args.figure_format not in ALLOWED_FIGURE_FORMATS:
        msg = f"--figure-format must be one of {sorted(ALLOWED_FIGURE_FORMATS)}"
        raise ValueError(msg)
    if args.expected_slides is not None and args.expected_slides < 1:
        msg = "--expected-slides must be >= 1"
        raise ValueError(msg)
    if not 72 <= args.ppi <= 600:
        msg = "--ppi must be between 72 and 600"
        raise ValueError(msg)

    deck_dir = deck_path.parent
    issues: list[str] = []
    for typ_file in collect_typ_files(deck_dir):
        rel_label = typ_file.relative_to(deck_dir).as_posix()
        issues.extend(scan_typst_escaping_issues(typ_file.read_text(encoding="utf-8"), label=rel_label))
    if issues:
        if args.json_output:
            sys.stdout.write(json.dumps({"ok": False, "issues": issues}, indent=2) + "\n")
        raise ValueError("; ".join(issues))

    fonts = discover_font_paths(deck_path, args.font_path)
    font_args = _typst_font_args(fonts)

    rendered_figures: list[str] = []
    if args.render_figures:
        figures_dir = deck_dir / "figures"
        if figures_dir.is_dir():
            for fig_src in sorted(figures_dir.glob("*.typ")):
                fig_out = fig_src.with_suffix(f".{args.figure_format}")
                cmd = ["compile", "--root", str(deck_dir), *font_args, "--format", args.figure_format]
                if args.figure_format == "png":
                    cmd.extend(["--ppi", str(args.ppi)])
                cmd.extend([str(fig_src), str(fig_out)])
                proc = _run_typst(cmd)
                if proc.returncode != 0:
                    detail = " ".join((proc.stderr or proc.stdout).split())[-400:]
                    msg = f"Error compiling figure {fig_src.name}: {detail}"
                    raise RuntimeError(msg)
                rendered_figures.append(str(fig_out))

    pdf_path = (args.output or deck_path.with_suffix(".pdf")).resolve()
    source_typ_paths = {deck_path, *(p.resolve() for p in collect_typ_files(deck_dir))}
    if pdf_path in source_typ_paths or pdf_path.suffix.lower() == ".typ":
        msg = f"Output PDF path must differ from Typst source files: {args.output or pdf_path}"
        raise ValueError(msg)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = (args.png_dir or (deck_dir / "_preview")).resolve()
    preview_dir.mkdir(parents=True, exist_ok=True)
    stem = deck_path.stem
    for stale_png in preview_dir.glob(f"{stem}-*.png"):
        stale_png.unlink()

    pdf_proc = _run_typst(["compile", "--root", str(deck_dir), *font_args, str(deck_path), str(pdf_path)])
    if pdf_proc.returncode != 0:
        detail = " ".join((pdf_proc.stderr or pdf_proc.stdout).split())[-400:]
        msg = f"Typst PDF compile failed: {detail}"
        raise RuntimeError(msg)

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
        msg = f"Typst PNG render failed: {detail}"
        raise RuntimeError(msg)

    png_files = sorted(
        preview_dir.glob(f"{stem}-*.png"),
        key=lambda p: int(p.stem.rsplit("-", 1)[-1]) if p.stem.rsplit("-", 1)[-1].isdigit() else 0,
    )
    slide_count = len(png_files)
    if slide_count == 0:
        msg = f"Typst produced zero PNG preview slides in {preview_dir}"
        raise RuntimeError(msg)

    warnings = [line for line in (pdf_proc.stderr or "").splitlines() if "warning:" in line.lower()]
    syntax_warnings = [w for w in warnings if "no text within stars" in w.lower()]
    font_warnings = [w for w in warnings if "unknown font family" in w.lower()]
    overflow = args.expected_slides is not None and slide_count != args.expected_slides
    strict_fonts = not args.allow_font_warnings

    ok = not overflow and not syntax_warnings and (not font_warnings or not strict_fonts)
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
        "warnings": warnings,
    }
    _emit(payload, json_output=args.json_output)

    if syntax_warnings:
        msg = "Typst markup warning: found empty bold stars (`**...**`). Typst uses single `*bold*`."
        raise ValueError(msg)
    if font_warnings and strict_fonts:
        msg = (
            "Typst font warning: missing required font family ("
            + "; ".join(font_warnings)
            + "). Pass --font-path or install the theme fonts (or use --allow-font-warnings explicitly)."
        )
        raise RuntimeError(msg)
    if overflow:
        msg = (
            f"Overflow/mismatch: expected {args.expected_slides} slides, compiled {slide_count}. "
            f"Inspect {preview_dir} for clipped or spilled content."
        )
        raise ValueError(msg)
    return payload


def run_upload(args: argparse.Namespace) -> dict[str, Any]:
    """Validate PDF bytes, stage in a private temp directory, upload via gws, and verify MD5/size parity."""
    pdf_arg: Path = args.pdf
    pdf_path = pdf_arg.resolve()
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        msg = f"Input must be an existing .pdf file: {pdf_arg}"
        raise ValueError(msg)
    if not args.drive_folder and not args.file_id:
        msg = "Specify --file-id <FILE_ID> or --drive-folder <FOLDER_ID>."
        raise ValueError(msg)

    with pdf_path.open("rb") as handle:
        magic = handle.read(5)
    if magic != b"%PDF-":
        msg = f"File does not start with valid %PDF- header: {pdf_path}"
        raise ValueError(msg)

    local_md5, local_size = _file_md5_and_size(pdf_path)
    if local_size == 0:
        msg = f"PDF file is empty: {pdf_path}"
        raise ValueError(msg)

    valid_folder = _validate_drive_id(args.drive_folder, "folder ID") if args.drive_folder else None
    valid_file_id = _validate_drive_id(args.file_id, "file ID") if args.file_id else None
    upload_name = _validate_upload_name(args.name or pdf_path.name)

    if args.dry_run:
        payload: dict[str, Any] = {
            "dry_run": True,
            "pdf": str(pdf_path),
            "name": upload_name,
            "target_file_id": valid_file_id,
            "drive_folder": valid_folder,
            "local_md5": local_md5,
            "local_size": local_size,
            "protect_copy": args.protect_copy,
        }
        _emit(payload, json_output=args.json_output)
        return payload

    fields = "id,name,mimeType,version,modifiedTime,webViewLink,md5Checksum,size,copyRequiresWriterPermission"
    # gws reads `.env` from cwd upward and rejects `--upload` paths outside cwd; run every call from one private tempdir.
    with tempfile.TemporaryDirectory(prefix="typst-deck-upload-") as tmp_dir_str:
        gws_dir = Path(tmp_dir_str)
        staged = gws_dir / upload_name
        shutil.copyfile(pdf_path, staged)

        target_id = valid_file_id
        if not target_id and valid_folder:
            target_id = _find_existing_file_in_folder(valid_folder, upload_name, cwd=gws_dir)

        if target_id:
            meta_body: dict[str, Any] = {}
            if args.name:
                meta_body["name"] = upload_name
            if args.protect_copy:
                meta_body["copyRequiresWriterPermission"] = True
            update_cmd = [
                "drive",
                "files",
                "update",
                "--params",
                json.dumps({"fileId": target_id, "supportsAllDrives": True, "fields": fields}),
            ]
            if meta_body:
                update_cmd.extend(["--json", json.dumps(meta_body)])
            update_cmd.extend(["--upload", staged.name, "--upload-content-type", "application/pdf"])
            res = _run_gws(update_cmd, cwd=gws_dir)
            operation = "updated"
        else:
            if not valid_folder:
                msg = "Cannot create a new Drive file without --drive-folder."
                raise ValueError(msg)
            create_body: dict[str, Any] = {
                "name": upload_name,
                "mimeType": "application/pdf",
                "parents": [valid_folder],
            }
            if args.protect_copy:
                create_body["copyRequiresWriterPermission"] = True
            res = _run_gws(
                [
                    "drive",
                    "files",
                    "create",
                    "--params",
                    json.dumps({"supportsAllDrives": True, "fields": fields}),
                    "--json",
                    json.dumps(create_body),
                    "--upload",
                    staged.name,
                    "--upload-content-type",
                    "application/pdf",
                ],
                cwd=gws_dir,
            )
            operation = "created"

        uploaded_id = str(res["id"])
        verified = _run_gws(
            [
                "drive",
                "files",
                "get",
                "--params",
                json.dumps({"fileId": uploaded_id, "supportsAllDrives": True, "fields": fields}),
            ],
            cwd=gws_dir,
        )

    remote_md5 = str(verified.get("md5Checksum") or "")
    remote_size = int(verified.get("size") or 0)
    if remote_md5 != local_md5 or remote_size != local_size:
        msg = (
            f"Integrity mismatch after upload: local ({local_md5}, {local_size} B) != "
            f"remote ({remote_md5}, {remote_size} B)."
        )
        raise RuntimeError(msg)

    result: dict[str, Any] = {
        "ok": True,
        "operation": operation,
        "file_id": uploaded_id,
        "name": verified.get("name"),
        "web_view_link": verified.get("webViewLink"),
        "md5Checksum": remote_md5,
        "size": remote_size,
        "copyRequiresWriterPermission": verified.get("copyRequiresWriterPermission"),
        "reminder": "Verify ACLs via `gws drive permissions list` before widening access.",
    }
    _emit(result, json_output=args.json_output)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
        suggest_on_error=True,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_p = subparsers.add_parser(
        "check",
        help="Validate Typst escaping, compile figures/PDF/PNGs, and check slide count and font warnings.",
        allow_abbrev=False,
    )
    check_p.add_argument("deck", type=Path, help="Main Typst deck source (.typ).")
    check_p.add_argument("-o", "--output", type=Path, default=None, help="Compiled PDF output path.")
    check_p.add_argument(
        "--expected-slides",
        type=int,
        default=None,
        help="Fail if rendered page count differs from N.",
    )
    check_p.add_argument(
        "--png-dir",
        type=Path,
        default=None,
        help="Directory for PNG slide previews (default: <deck_dir>/_preview).",
    )
    check_p.add_argument("--ppi", type=int, default=192, help="PNG preview resolution (72-600, default: 192).")
    check_p.add_argument(
        "--render-figures",
        action="store_true",
        help="Compile figures/*.typ before compiling the main deck.",
    )
    check_p.add_argument(
        "--figure-format",
        default="svg",
        choices=sorted(ALLOWED_FIGURE_FORMATS),
        help="Figure output format when --render-figures is set (default: svg).",
    )
    check_p.add_argument(
        "--font-path",
        type=Path,
        action="append",
        default=None,
        help="Additional Typst font directory (repeatable).",
    )
    check_p.add_argument(
        "--allow-font-warnings",
        action="store_true",
        help="Allow Typst `unknown font family` warnings instead of failing closed.",
    )
    check_p.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")

    upload_p = subparsers.add_parser(
        "upload",
        help="Stage a validated PDF in a private tempdir, upload via gws, and verify MD5/size parity.",
        allow_abbrev=False,
    )
    upload_p.add_argument("pdf", type=Path, help="Compiled PDF file to upload to Google Drive.")
    upload_p.add_argument(
        "--drive-folder",
        default=None,
        help="Target Google Drive folder ID (creates or updates existing file by name).",
    )
    upload_p.add_argument(
        "--file-id",
        default=None,
        help="Existing Google Drive file ID to update in place (preserves URL).",
    )
    upload_p.add_argument("--name", default=None, help="Remote Drive filename (defaults to PDF filename).")
    upload_p.add_argument(
        "--protect-copy",
        action="store_true",
        help="Set copyRequiresWriterPermission=true on the uploaded Drive file.",
    )
    upload_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print plan without modifying Drive.",
    )
    upload_p.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON on stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            run_check(args)
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
