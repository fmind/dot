#!/usr/bin/env python3
"""Validate, compile, export PPTX/PNGs, and safely upload Typst 16:9 slide decks to Drive/Google Slides."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import unescape as xml_unescape

DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")
FORBIDDEN_RAW_ESCAPE_RE = re.compile(r"\\[$~*]")
ODD_STRING_ESCAPE_RE = re.compile(r"(?<!\\)(?:\\\\)*\\([$~*])")
ALLOWED_FIGURE_FORMATS = frozenset({"svg", "png"})

PDF_MIME = "application/pdf"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"
FOLDER_MIME = "application/vnd.google-apps.folder"
SLIDE_CX = 9144000  # 10 in at 914400 EMU/in (16:9 widescreen)
SLIDE_CY = 5143500  # 5.625 in

_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


_TYPST_STMT_KEYWORDS = frozenset({"context", "for", "if", "import", "include", "let", "return", "set", "show", "while"})


def _scan_typst_raw(source: str, i: int, line: int, label: str, issues: list[str]) -> tuple[int, int]:
    tick_count = 1
    while i + tick_count < len(source) and source[i + tick_count] == "`":
        tick_count += 1
    start_line = line
    i += tick_count
    fence = "`" * tick_count
    close_idx = source.find(fence, i)
    if close_idx == -1:
        return len(source), line + source[i:].count("\n")
    body = source[i:close_idx]
    if tick_count == 1:
        issues.extend(
            f"{label}:{start_line}: remove backslash in inline raw span `{match.group(0)}`; "
            "Typst renders literal backslashes inside backticks."
            for match in FORBIDDEN_RAW_ESCAPE_RE.finditer(body)
        )
    return close_idx + tick_count, line + body.count("\n")


def _scan_typst_string(source: str, i: int, line: int, label: str, issues: list[str]) -> tuple[int, int]:
    start_line = line
    i += 1
    chars: list[str] = []
    while i < len(source):
        curr = source[i]
        if curr == "\\" and i + 1 < len(source):
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
    return i, line


def scan_typst_escaping_issues(source: str, label: str = "<deck>") -> list[str]:
    """Flag backslash escapes ($, ~, *) inside Typst code string literals or inline raw spans."""
    issues: list[str] = []
    n = len(source)
    i = 0
    line = 1
    modes: list[str] = ["markup"]

    while i < n:
        ch = source[i]
        mode = modes[-1]
        if ch == "\n":
            line += 1
            i += 1
            if modes[-1] in {"stmt", "call"}:
                modes.pop()
            continue

        if mode == "call":
            if ch in " \t":
                j = i
                while j < n and source[j] in " \t":
                    j += 1
                if j < n and source[j] == "[":
                    i = j
                    continue
                modes.pop()
                continue
            if ch == "(":
                modes.append("paren")
                i += 1
                continue
            if ch == "[":
                modes.append("content")
                i += 1
                continue
            if ch == "." and i + 1 < n and (source[i + 1].isalpha() or source[i + 1] == "_"):
                i += 1
                while i < n and (source[i].isalnum() or source[i] in "_-"):
                    i += 1
                continue
            modes.pop()
            continue

        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            end = source.find("\n", i + 2)
            i = n if end == -1 else end
            continue

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

        if ch == "`":
            i, line = _scan_typst_raw(source, i, line, label, issues)
            continue

        if mode in {"markup", "content"}:
            if ch == "\\" and i + 1 < n:
                if source[i + 1] == "\n":
                    line += 1
                i += 2
                continue
            if mode == "content":
                if ch == "[":
                    modes.append("content")
                    i += 1
                    continue
                if ch == "]":
                    modes.pop()
                    i += 1
                    continue
            if ch == "#":
                i += 1
                if i >= n:
                    break
                nxt = source[i]
                if nxt == "{":
                    modes.append("brace")
                    i += 1
                elif nxt == "(":
                    modes.append("paren")
                    i += 1
                elif nxt == "[":
                    modes.append("content")
                    i += 1
                elif nxt == '"':
                    i, line = _scan_typst_string(source, i, line, label, issues)
                elif nxt.isalpha() or nxt == "_":
                    start = i
                    while i < n and (source[i].isalnum() or source[i] in "_-"):
                        i += 1
                    ident = source[start:i]
                    modes.append("stmt" if ident in _TYPST_STMT_KEYWORDS else "call")
                continue
            i += 1
            continue

        # Code modes: "stmt", "paren", "brace"
        if ch == '"':
            i, line = _scan_typst_string(source, i, line, label, issues)
            continue
        if mode == "stmt" and (closing := {"]": "content", ")": "paren", "}": "brace"}.get(ch)) and closing in modes:
            modes.pop()
            continue
        if ch == "(":
            modes.append("paren")
        elif ch == ")" and mode == "paren":
            modes.pop()
        elif ch == "{":
            modes.append("brace")
        elif ch == "}" and mode == "brace":
            modes.pop()
        elif ch == "[":
            modes.append("content")
        elif ch == ";" and mode == "stmt":
            modes.pop()
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
    """Collect deck-root and figures .typ files for static validation or source archival."""
    files = sorted(p for p in deck_dir.glob("*.typ") if p.is_file())
    figures_dir = deck_dir / "figures"
    if figures_dir.is_dir():
        files.extend(sorted(p for p in figures_dir.glob("*.typ") if p.is_file()))
    return files


def collect_source_files(deck_dir: Path) -> list[Path]:
    """Collect .typ sources (root + figures/*.typ) and root .py deck scripts (excluding __init__.py)."""
    py_files = sorted(p for p in deck_dir.glob("*.py") if p.is_file() and p.name != "__init__.py")
    return [*collect_typ_files(deck_dir), *py_files]


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


def query_deck_info(
    deck_path: Path, deck_dir: Path, font_args: list[str]
) -> tuple[dict[int, str], str | None, dict[int, int]]:
    """Extract speaker notes, deck title, and per-slide visible word counts via a single `typst eval` call."""
    expr = (
        "(notes: query(<fmind-speaker-note>).map(it => it.value), "
        "meta: query(<fmind-deck-meta>).map(it => it.value), "
        "words: query(<fmind-slide-words>).map(it => it.value))"
    )
    proc = _run_typst(
        [
            "eval",
            expr,
            "--root",
            str(deck_dir),
            *font_args,
            "--in",
            str(deck_path),
            "--format",
            "json",
        ]
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        msg = f"Typst metadata query failed: {detail}"
        raise RuntimeError(msg)
    raw = proc.stdout.strip()
    payload = json.loads(raw) if raw else {}
    notes_by_page: dict[int, list[str]] = {}
    deck_title: str | None = None
    words_by_page: dict[int, int] = {}
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
    notes = {page: "\n\n".join(parts) for page, parts in sorted(notes_by_page.items())}
    return notes, deck_title, dict(sorted(words_by_page.items()))


def _rels_xml(entries: list[tuple[str, str, str]]) -> bytes:
    items = "".join(
        f'<Relationship Id="{xml_escape(rid)}" Type="{xml_escape(rtype)}" Target="{xml_escape(target)}"/>'
        for rid, rtype, target in entries
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{_NS_REL}">{items}</Relationships>'
    ).encode()


def _notes_slide_xml(note_text: str) -> bytes:
    paragraphs = note_text.splitlines() if note_text else []
    if not paragraphs:
        p_xml = '<a:p><a:endParaRPr lang="en-US"/></a:p>'
    else:
        p_xml = "".join(
            f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{xml_escape(line)}</a:t></a:r></a:p>'
            if line
            else '<a:p><a:endParaRPr lang="en-US"/></a:p>'
            for line in paragraphs
        )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:notes xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
        f"<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{p_xml}</p:txBody></p:sp>"
        "</p:spTree></p:cSld></p:notes>"
    ).encode()


def _slide_xml(index: int) -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f'<p:pic><p:nvPicPr><p:cNvPr id="2" name="Slide {index}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId2" cstate="print"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_CX}" cy="{SLIDE_CY}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        "</p:spTree></p:cSld></p:sld>"
    ).encode()


def build_pptx(
    slide_pngs: list[Path],
    output_pptx: Path,
    *,
    title: str,
    speaker_notes: dict[int, str] | None = None,
) -> Path:
    """Pack rendered 16:9 PNG slides and optional per-slide speaker notes into a stdlib OOXML .pptx."""
    if not slide_pngs:
        msg = "Cannot build .pptx with zero slide PNGs."
        raise ValueError(msg)
    notes = speaker_notes or {}
    output_pptx.parent.mkdir(parents=True, exist_ok=True)
    n = len(slide_pngs)

    content_overrides = [
        ("/ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
        (
            "/ppt/slideMasters/slideMaster1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml",
        ),
        (
            "/ppt/slideLayouts/slideLayout1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml",
        ),
        (
            "/ppt/notesMasters/notesMaster1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
        ),
        ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
    ]
    for idx in range(1, n + 1):
        content_overrides.append(
            (f"/ppt/slides/slide{idx}.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
        )
        content_overrides.append(
            (
                f"/ppt/notesSlides/notesSlide{idx}.xml",
                "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
            )
        )
    content_types = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{_NS_CT}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + "".join(f'<Override PartName="{p}" ContentType="{ct}"/>' for p, ct in content_overrides)
        + "</Types>"
    ).encode("utf-8")

    pres_rels = [("rId1", f"{_NS_OD_REL}/slideMaster", "slideMasters/slideMaster1.xml")]
    sld_ids = []
    for idx in range(1, n + 1):
        rid = f"rId{idx + 1}"
        pres_rels.append((rid, f"{_NS_OD_REL}/slide", f"slides/slide{idx}.xml"))
        sld_ids.append(f'<p:sldId id="{255 + idx}" r:id="{rid}"/>')
    notes_master_rid = f"rId{n + 2}"
    theme_rid = f"rId{n + 3}"
    pres_rels.append((notes_master_rid, f"{_NS_OD_REL}/notesMaster", "notesMasters/notesMaster1.xml"))
    pres_rels.append((theme_rid, f"{_NS_OD_REL}/theme", "theme/theme1.xml"))

    presentation_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f'<p:notesMasterIdLst><p:notesMasterId r:id="{notes_master_rid}"/></p:notesMasterIdLst>'
        f"<p:sldIdLst>{''.join(sld_ids)}</p:sldIdLst>"
        f'<p:sldSz cx="{SLIDE_CX}" cy="{SLIDE_CY}" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    ).encode()

    theme_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="{_NS_A}" name="Fmind">'
        '<a:themeElements><a:clrScheme name="Fmind">'
        '<a:dk1><a:srgbClr val="202124"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="595D62"/></a:dk2><a:lt2><a:srgbClr val="F1F3F4"/></a:lt2>'
        '<a:accent1><a:srgbClr val="174EA6"/></a:accent1><a:accent2><a:srgbClr val="00636D"/></a:accent2>'
        '<a:accent3><a:srgbClr val="934900"/></a:accent3><a:accent4><a:srgbClr val="0D652D"/></a:accent4>'
        '<a:accent5><a:srgbClr val="681DA8"/></a:accent5><a:accent6><a:srgbClr val="A50E0E"/></a:accent6>'
        '<a:hlink><a:srgbClr val="174EA6"/></a:hlink><a:folHlink><a:srgbClr val="681DA8"/></a:folHlink>'
        '</a:clrScheme><a:fontScheme name="Fmind"><a:majorFont><a:latin typeface="Google Sans"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Google Sans"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="Fmind"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
        '<a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
        "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>"
        '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
        "</a:fmtScheme></a:themeElements></a:theme>"
    ).encode()

    slide_master_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldMaster xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        '<p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld>"
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        "</p:sldMaster>"
    ).encode()

    slide_layout_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldLayout xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}" type="blank" preserve="1">'
        '<p:cSld name="Blank"><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld></p:sldLayout>"
    ).encode()

    notes_master_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:notesMaster xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld>"
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        "</p:notesMaster>"
    ).encode()

    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{xml_escape(title)}</dc:title></cp:coreProperties>"
    ).encode()

    with zipfile.ZipFile(output_pptx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr(
            "_rels/.rels",
            _rels_xml(
                [
                    ("rId1", f"{_NS_OD_REL}/officeDocument", "ppt/presentation.xml"),
                    (
                        "rId2",
                        "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
                        "docProps/core.xml",
                    ),
                ]
            ),
        )
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", _rels_xml(pres_rels))
        zf.writestr("ppt/theme/theme1.xml", theme_xml)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml)
        zf.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            _rels_xml(
                [
                    ("rId1", f"{_NS_OD_REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
                    ("rId2", f"{_NS_OD_REL}/theme", "../theme/theme1.xml"),
                ]
            ),
        )
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml)
        zf.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            _rels_xml([("rId1", f"{_NS_OD_REL}/slideMaster", "../slideMasters/slideMaster1.xml")]),
        )
        zf.writestr("ppt/notesMasters/notesMaster1.xml", notes_master_xml)
        zf.writestr(
            "ppt/notesMasters/_rels/notesMaster1.xml.rels",
            _rels_xml([("rId1", f"{_NS_OD_REL}/theme", "../theme/theme1.xml")]),
        )
        for idx, png_path in enumerate(slide_pngs, start=1):
            media_name = f"slide-{idx:02d}.png"
            zf.writestr(f"ppt/media/{media_name}", png_path.read_bytes(), compress_type=zipfile.ZIP_STORED)
            zf.writestr(f"ppt/slides/slide{idx}.xml", _slide_xml(idx))
            zf.writestr(
                f"ppt/slides/_rels/slide{idx}.xml.rels",
                _rels_xml(
                    [
                        ("rId1", f"{_NS_OD_REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
                        ("rId2", f"{_NS_OD_REL}/image", f"../media/{media_name}"),
                        ("rId3", f"{_NS_OD_REL}/notesSlide", f"../notesSlides/notesSlide{idx}.xml"),
                    ]
                ),
            )
            zf.writestr(f"ppt/notesSlides/notesSlide{idx}.xml", _notes_slide_xml(notes.get(idx, "")))
            zf.writestr(
                f"ppt/notesSlides/_rels/notesSlide{idx}.xml.rels",
                _rels_xml(
                    [
                        ("rId1", f"{_NS_OD_REL}/slide", f"../slides/slide{idx}.xml"),
                        ("rId2", f"{_NS_OD_REL}/notesMaster", "../notesMasters/notesMaster1.xml"),
                    ]
                ),
            )
    return output_pptx


def inspect_pptx_metadata(pptx_path: Path) -> tuple[int, str | None]:
    """Validate an OOXML .pptx archive and return `(slide_count, core_title)`."""
    try:
        with zipfile.ZipFile(pptx_path, "r") as zf:
            names = set(zf.namelist())
            core_xml = (
                zf.read("docProps/core.xml").decode("utf-8", errors="replace") if "docProps/core.xml" in names else ""
            )
    except zipfile.BadZipFile as exc:
        msg = f"File is not a valid .pptx OOXML archive: {pptx_path}"
        raise ValueError(msg) from exc
    if "ppt/presentation.xml" not in names:
        msg = f"Archive is missing ppt/presentation.xml: {pptx_path}"
        raise ValueError(msg)
    slides = [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    if not slides:
        msg = f".pptx contains zero slides: {pptx_path}"
        raise ValueError(msg)
    title: str | None = None
    if core_xml and (
        match := re.search(r"<(?:[A-Za-z0-9_-]+:)?title[^>]*>(.*?)</(?:[A-Za-z0-9_-]+:)?title>", core_xml, re.DOTALL)
    ):
        parsed = xml_unescape(match.group(1)).strip()
        if parsed:
            title = parsed
    return len(slides), title


def _validate_drive_id(value: str, label: str) -> str:
    cleaned = value.strip()
    if not DRIVE_ID_RE.fullmatch(cleaned):
        msg = f"Invalid Google Drive {label}: {value!r}"
        raise ValueError(msg)
    return cleaned


def _validate_upload_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."} or cleaned.startswith("-") or "/" in cleaned or "\\" in cleaned:
        msg = f"Remote filename must be a plain filename without path separators or leading '-': {value!r}"
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


def _find_existing_file_in_folder(
    parent_id: str,
    name: str,
    *,
    mime_type: str | None = None,
    cwd: Path,
) -> str | None:
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    mime_clause = f"mimeType = '{_escape_drive_q(mime_type)}'" if mime_type else f"mimeType != '{FOLDER_MIME}'"
    query = f"trashed = false and {mime_clause} and '{valid_parent}' in parents and name = '{_escape_drive_q(name)}'"
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": query,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    matches: list[str] = []
    while True:
        resp = _run_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=cwd)
        files = resp.get("files") or []
        matches.extend(str(item["id"]) for item in files)
        token = resp.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token
    if len(matches) > 1:
        msg = f"Multiple non-trashed Drive files named {name!r} in folder {valid_parent}: {matches}; pass --file-id explicitly."
        raise RuntimeError(msg)
    return matches[0] if matches else None


def _ensure_drive_folder(parent_id: str, name: str, *, cwd: Path) -> str:
    existing = _find_existing_file_in_folder(parent_id, name, mime_type=FOLDER_MIME, cwd=cwd)
    if existing:
        return existing
    created = _run_gws(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": "id,name"}),
            "--json",
            json.dumps({"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}),
        ],
        cwd=cwd,
    )
    return str(created["id"])


def _upload_binary_file(
    local_path: Path,
    *,
    upload_name: str,
    upload_mime: str,
    target_mime: str,
    parent_folder: str | None,
    target_file_id: str | None,
    protect_copy: bool,
    rename: bool,
    cwd: Path,
    fields: str,
) -> tuple[str, str]:
    staged = cwd / upload_name
    shutil.copyfile(local_path, staged)
    resolved_id = target_file_id
    if not resolved_id and parent_folder:
        resolved_id = _find_existing_file_in_folder(parent_folder, upload_name, mime_type=target_mime, cwd=cwd)

    if resolved_id:
        meta_body: dict[str, Any] = {}
        if rename:
            meta_body["name"] = upload_name
        if protect_copy:
            meta_body["copyRequiresWriterPermission"] = True
        cmd = [
            "drive",
            "files",
            "update",
            "--params",
            json.dumps({"fileId": resolved_id, "supportsAllDrives": True, "fields": fields}),
        ]
        if meta_body:
            cmd.extend(["--json", json.dumps(meta_body)])
        cmd.extend(["--upload", staged.name, "--upload-content-type", upload_mime])
        res = _run_gws(cmd, cwd=cwd)
        return str(res["id"]), "updated"

    if not parent_folder:
        msg = "Cannot create a new Drive file without --drive-folder."
        raise ValueError(msg)
    create_body: dict[str, Any] = {
        "name": upload_name,
        "mimeType": target_mime,
        "parents": [parent_folder],
    }
    if protect_copy:
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
            upload_mime,
        ],
        cwd=cwd,
    )
    return str(res["id"]), "created"


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
        msg = "Typst markup warning: found empty bold stars (`**...**`). Typst uses single `*bold*`."
        raise ValueError(msg)
    if font_warnings and strict_fonts:
        msg = (
            "Typst font warning: missing required font family ("
            + "; ".join(font_warnings)
            + "). Pass --font-path or install the theme fonts (or use --allow-font-warnings explicitly)."
        )
        raise RuntimeError(msg)
    if other_warnings:
        msg = "Typst emitted unexpected warnings: " + "; ".join(other_warnings)
        raise RuntimeError(msg)


def run_render(args: argparse.Namespace) -> dict[str, Any]:
    """Validate escaping, compile a standalone .typ visual card to PNG/SVG, and check font/syntax warnings."""
    source_arg: Path = args.source
    source_path = source_arg.resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".typ":
        msg = f"Typst source file must be an existing .typ file: {source_arg}"
        raise ValueError(msg)
    if args.format not in ALLOWED_FIGURE_FORMATS:
        msg = f"--format must be one of {sorted(ALLOWED_FIGURE_FORMATS)}"
        raise ValueError(msg)
    if not 72 <= args.ppi <= 600:
        msg = "--ppi must be between 72 and 600"
        raise ValueError(msg)

    root_dir = (args.root or source_path.parent).resolve()
    if not source_path.is_relative_to(root_dir):
        msg = f"Typst source must reside inside --root ({root_dir}): {source_path}"
        raise ValueError(msg)
    out_path = (args.output or source_path.with_suffix(f".{args.format}")).resolve()
    if out_path == source_path or out_path.suffix.lower() == ".typ":
        msg = f"Output path must differ from Typst source files: {args.output or out_path}"
        raise ValueError(msg)

    issues = scan_typst_escaping_issues(source_path.read_text(encoding="utf-8"), label=source_path.name)
    if issues:
        if args.json_output:
            sys.stdout.write(json.dumps({"ok": False, "issues": issues}, indent=2) + "\n")
        raise ValueError("; ".join(issues))

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
        msg = f"Error rendering {source_path.name}: {detail}"
        raise RuntimeError(msg)

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
    _raise_on_typst_warnings(syntax_warnings, font_warnings, other_warnings, strict_fonts=strict_fonts)
    return payload


def run_check(args: argparse.Namespace) -> dict[str, Any]:
    """Validate Typst escaping, compile figures/PDF/PNGs (+ optional .pptx), and check warnings."""
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
    if args.max_words is not None and args.max_words < 1:
        msg = "--max-words must be >= 1"
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
    strict_fonts = not args.allow_font_warnings

    all_warnings: list[str] = []
    syntax_warnings: list[str] = []
    font_warnings: list[str] = []
    other_warnings: list[str] = []

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
                fw, f_syn, f_font, f_other = _collect_typst_warnings(proc.stderr or "")
                all_warnings.extend(f"{fig_src.name}: {w}" for w in fw)
                syntax_warnings.extend(f"{fig_src.name}: {w}" for w in f_syn)
                font_warnings.extend(f"{fig_src.name}: {w}" for w in f_font)
                other_warnings.extend(f"{fig_src.name}: {w}" for w in f_other)
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
    slide_png_re = re.compile(rf"^{re.escape(stem)}-(\d+)\.png$")
    for stale_png in preview_dir.iterdir():
        if stale_png.is_file() and slide_png_re.match(stale_png.name):
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

    png_pairs = [
        (int(match.group(1)), path)
        for path in preview_dir.iterdir()
        if path.is_file() and (match := slide_png_re.match(path.name))
    ]
    png_files = [path for _, path in sorted(png_pairs, key=lambda pair: pair[0])]
    slide_count = len(png_files)
    if slide_count == 0:
        msg = f"Typst produced zero PNG preview slides in {preview_dir}"
        raise RuntimeError(msg)

    pptx_path: Path | None = None
    notes_slides: list[int] = []
    slide_words: dict[int, int] = {}
    word_violations: dict[int, int] = {}
    if args.pptx is not None or args.max_words is not None:
        notes, meta_title, slide_words = query_deck_info(deck_path, deck_dir, font_args)
        if args.max_words is not None:
            if not slide_words:
                msg = "No <fmind-slide-words> metadata found; import fmind-slides.typ to enforce --max-words."
                raise ValueError(msg)
            word_violations = {page: count for page, count in slide_words.items() if count > args.max_words}
        if args.pptx is not None:
            pptx_target = pdf_path.with_suffix(".pptx") if str(args.pptx) == "__AUTO__" else args.pptx.resolve()
            if pptx_target in source_typ_paths or pptx_target.suffix.lower() == ".typ":
                msg = f"Output PPTX path must differ from Typst source files: {pptx_target}"
                raise ValueError(msg)
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
    _emit(payload, json_output=args.json_output)

    _raise_on_typst_warnings(syntax_warnings, font_warnings, other_warnings, strict_fonts=strict_fonts)
    if word_violations:
        details = ", ".join(f"slide {page}: {count} words" for page, count in sorted(word_violations.items()))
        msg = f"Slide word limit exceeded (max {args.max_words}): {details}"
        raise ValueError(msg)
    if overflow:
        msg = (
            f"Overflow/mismatch: expected {args.expected_slides} slides, compiled {slide_count}. "
            f"Inspect {preview_dir} for clipped or spilled content."
        )
        raise ValueError(msg)
    return payload


def run_upload(args: argparse.Namespace) -> dict[str, Any]:
    """Validate .pdf or .pptx bytes, stage in a private tempdir, upload via gws, and verify read-back."""
    artifact_arg: Path = args.artifact
    artifact_path = artifact_arg.resolve()
    suffix = artifact_path.suffix.lower()
    if not artifact_path.is_file() or suffix not in {".pdf", ".pptx"}:
        msg = f"Input must be an existing .pdf or .pptx file: {artifact_arg}"
        raise ValueError(msg)
    if args.google_slides and suffix != ".pptx":
        msg = "--google-slides requires a .pptx file (compile one with 'check --pptx' or python-pptx)."
        raise ValueError(msg)
    if not args.drive_folder and not args.file_id:
        msg = "Specify --file-id <FILE_ID> or --drive-folder <FOLDER_ID>."
        raise ValueError(msg)

    expected_slides: int | None = None
    if suffix == ".pdf":
        with artifact_path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                msg = f"File does not start with valid %PDF- header: {artifact_path}"
                raise ValueError(msg)
        upload_mime = PDF_MIME
        target_mime = PDF_MIME
        default_name = artifact_path.name
    else:
        expected_slides, pptx_title = inspect_pptx_metadata(artifact_path)
        upload_mime = PPTX_MIME
        target_mime = GOOGLE_SLIDES_MIME if args.google_slides else PPTX_MIME
        if args.google_slides:
            default_name = (
                pptx_title if (pptx_title and pptx_title not in {"Deck", artifact_path.stem}) else artifact_path.stem
            )
        else:
            default_name = artifact_path.name

    local_md5, local_size = _file_md5_and_size(artifact_path)
    if local_size == 0:
        msg = f"Artifact file is empty: {artifact_path}"
        raise ValueError(msg)

    source_files: list[Path] = []
    if args.source_dir is not None:
        source_root = args.source_dir.resolve()
        if not source_root.is_dir():
            msg = f"--source-dir does not exist or is not a directory: {args.source_dir}"
            raise ValueError(msg)
        source_files = collect_source_files(source_root)
        if not source_files:
            msg = f"No .typ or .py source files found under --source-dir: {args.source_dir}"
            raise ValueError(msg)

    valid_folder = _validate_drive_id(args.drive_folder, "folder ID") if args.drive_folder else None
    valid_file_id = _validate_drive_id(args.file_id, "file ID") if args.file_id else None
    upload_name = _validate_upload_name(args.name or default_name)

    if args.dry_run:
        payload: dict[str, Any] = {
            "dry_run": True,
            "artifact": str(artifact_path),
            "name": upload_name,
            "target_mime": target_mime,
            "google_slides": args.google_slides,
            "target_file_id": valid_file_id,
            "drive_folder": valid_folder,
            "local_md5": local_md5,
            "local_size": local_size,
            "protect_copy": args.protect_copy,
        }
        if expected_slides is not None:
            payload["expected_slides"] = expected_slides
        if source_files:
            payload["source_files"] = [str(p.relative_to(args.source_dir.resolve())) for p in source_files]
        _emit(payload, json_output=args.json_output)
        return payload

    fields = "id,name,mimeType,version,modifiedTime,webViewLink,md5Checksum,size,copyRequiresWriterPermission,trashed,parents"
    with tempfile.TemporaryDirectory(prefix="typst-deck-upload-") as tmp_dir_str:
        gws_dir = Path(tmp_dir_str)
        uploaded_id, operation = _upload_binary_file(
            artifact_path,
            upload_name=upload_name,
            upload_mime=upload_mime,
            target_mime=target_mime,
            parent_folder=valid_folder,
            target_file_id=valid_file_id,
            protect_copy=args.protect_copy,
            rename=bool(args.name),
            cwd=gws_dir,
            fields=fields,
        )
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
        if verified.get("trashed") is True:
            msg = f"Uploaded file is marked trashed in Drive: {uploaded_id}"
            raise RuntimeError(msg)

        slides_count: int | None = None
        if args.google_slides:
            remote_mime = str(verified.get("mimeType") or "")
            if remote_mime != GOOGLE_SLIDES_MIME:
                msg = f"Expected Google Slides mimeType {GOOGLE_SLIDES_MIME}, got {remote_mime!r}"
                raise RuntimeError(msg)
            slides_doc = _run_gws(
                [
                    "slides",
                    "presentations",
                    "get",
                    "--params",
                    json.dumps({"presentationId": uploaded_id, "fields": "presentationId,title,slides(objectId)"}),
                ],
                cwd=gws_dir,
            )
            slides_count = len(slides_doc.get("slides") or [])
            if slides_count != expected_slides:
                msg = f"Google Slides slide-count mismatch: expected {expected_slides}, got {slides_count}"
                raise RuntimeError(msg)
        else:
            remote_md5 = str(verified.get("md5Checksum") or "")
            remote_size = int(verified.get("size") or 0)
            if remote_md5 != local_md5 or remote_size != local_size:
                msg = (
                    f"Integrity mismatch after upload: local ({local_md5}, {local_size} B) != "
                    f"remote ({remote_md5}, {remote_size} B)."
                )
                raise RuntimeError(msg)

        synced_sources: list[dict[str, str]] = []
        if source_files:
            parent_for_assets = valid_folder or next(iter(verified.get("parents") or []), None)
            if not parent_for_assets:
                msg = "Cannot sync --source-dir without a resolved parent Drive folder ID."
                raise RuntimeError(msg)
            assets_id = _ensure_drive_folder(str(parent_for_assets), "assets", cwd=gws_dir)
            slug_folder_id = _ensure_drive_folder(assets_id, artifact_path.stem, cwd=gws_dir)
            source_root = args.source_dir.resolve()
            for src in source_files:
                rel_name = _validate_upload_name(src.relative_to(source_root).as_posix().replace("/", "__"))
                src_md5, src_size = _file_md5_and_size(src)
                src_id, src_op = _upload_binary_file(
                    src,
                    upload_name=rel_name,
                    upload_mime="text/plain",
                    target_mime="text/plain",
                    parent_folder=slug_folder_id,
                    target_file_id=None,
                    protect_copy=False,
                    rename=False,
                    cwd=gws_dir,
                    fields="id,md5Checksum,size",
                )
                src_get = _run_gws(
                    [
                        "drive",
                        "files",
                        "get",
                        "--params",
                        json.dumps({"fileId": src_id, "supportsAllDrives": True, "fields": "id,md5Checksum,size"}),
                    ],
                    cwd=gws_dir,
                )
                if str(src_get.get("md5Checksum") or "") != src_md5 or int(src_get.get("size") or 0) != src_size:
                    msg = f"Source integrity mismatch for {rel_name}"
                    raise RuntimeError(msg)
                synced_sources.append({"name": rel_name, "file_id": src_id, "operation": src_op})

    result: dict[str, Any] = {
        "ok": True,
        "operation": operation,
        "file_id": uploaded_id,
        "name": verified.get("name"),
        "mimeType": verified.get("mimeType"),
        "web_view_link": verified.get("webViewLink"),
        "copyRequiresWriterPermission": verified.get("copyRequiresWriterPermission"),
        "reminder": "Verify ACLs via `gws drive permissions list` before widening access.",
    }
    if args.google_slides:
        result["slide_count"] = slides_count
    else:
        result["md5Checksum"] = str(verified.get("md5Checksum") or "")
        result["size"] = int(verified.get("size") or 0)
    if synced_sources:
        result["synced_sources"] = synced_sources
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
