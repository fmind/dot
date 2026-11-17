"""Static Typst escaping validator, font discovery, Typst runner, and warning gate."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

FORBIDDEN_RAW_ESCAPE_RE = re.compile(r"\\[$~*]")
ODD_STRING_ESCAPE_RE = re.compile(r"(?<!\\)(?:\\\\)*\\([$~*])")
ALLOWED_FIGURE_FORMATS = frozenset({"svg", "png"})
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


def typst_font_args(font_paths: list[Path]) -> list[str]:
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


def query_deck_info(
    deck_path: Path,
    deck_dir: Path,
    font_args: list[str],
    *,
    run_typst_fn: Callable[[list[str]], subprocess.CompletedProcess[str]] = run_typst,
) -> tuple[dict[int, str], str | None, dict[int, int]]:
    """Extract speaker notes, deck title, and per-slide visible word counts via a single `typst eval` call."""
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


def collect_typst_warnings(stderr: str) -> tuple[list[str], list[str], list[str], list[str]]:
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


def raise_on_typst_warnings(
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


_TYPST_PROSE_FILTER = '.Name in ["Fmind.EmDash", "Fmind.SlopWords", "Fmind.SlopStyle", "Fmind.Wordiness"]'
_TYPST_SKIP_PREFIXES = ("//", "#import ", "#import(", "#let ", "#set ", "#show ")
_FRAMEWORK_TYP_FILES = frozenset({"fmind.typ", "fmind-slides.typ"})


def _resolve_vale_config(cwd: Path | None = None) -> Path | None:
    """Return the nearest project .vale.ini or the global ~/.config/vale/.vale.ini if present."""
    start = (cwd or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        candidate = parent / ".vale.ini"
        if candidate.is_file():
            return candidate
    global_cfg = Path.home() / ".config/vale/.vale.ini"
    return global_cfg if global_cfg.is_file() else None


def _strip_typst_preamble_and_comments(source: str) -> str:
    """Blank Typst preamble directives and line comments while keeping 1-based line numbers intact."""
    kept: list[str] = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(_TYPST_SKIP_PREFIXES):
            kept.append("")
        else:
            kept.append(line)
    return "\n".join(kept) + ("\n" if source.endswith("\n") else "")


def check_typst_prose_with_vale(typ_files: list[Path], *, base_dir: Path) -> tuple[list[str], list[str]]:
    """Run Vale anti-slop and em-dash checks across user .typ files, returning (errors, warnings)."""
    vale_bin = shutil.which("vale")
    if not vale_bin:
        return [], []
    config = _resolve_vale_config(base_dir)
    if config is None:
        return [], []
    errors: list[str] = []
    warnings: list[str] = []
    for path in typ_files:
        if path.name in _FRAMEWORK_TYP_FILES:
            continue
        prose = _strip_typst_preamble_and_comments(path.read_text(encoding="utf-8"))
        if not prose.strip():
            continue
        proc = subprocess.run(  # noqa: S603 - fixed Vale binary and resolved config path
            [
                vale_bin,
                "--no-global",
                "--config",
                str(config),
                "--output=JSON",
                "--ext=.txt",
                f"--filter={_TYPST_PROSE_FILTER}",
            ],
            input=prose,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if proc.returncode not in {0, 1}:
            detail = (proc.stderr or proc.stdout).strip()
            raise RuntimeError(f"vale failed on {path.name}: {detail}")
        raw = proc.stdout.strip()
        if not raw:
            continue
        label = path.relative_to(base_dir).as_posix() if path.is_relative_to(base_dir) else path.name
        for findings in json.loads(raw).values():
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
