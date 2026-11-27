#!/usr/bin/env python3
"""Read-only static security audit for an untrusted skill directory."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 5 * 1024 * 1024
HEAD_TAIL_BYTES = 256 * 1024
MAX_UNSAFE_CHARS_PER_FILE = 20
MAX_SNIPPET_CHARS = 160
MAX_SYMLINK_HOPS = 40

LINE_SPLIT_RE = re.compile(r"\r\n|\n|\r")
GIT_CONFIG_EXEC_RE = re.compile(
    r"(?i)(?:(?:^|[\s\]])(?:hooksPath|fsmonitor|[a-z0-9-]*command|pager|editor|clean|smudge|textconv|helper|process|askPass|gitProxy|cmd|driver|external|program|packObjectsHook|uploadpack|receivepack|sendmailCmd|tunnel|httpd|smtpServer)\s*=|"
    r"\[\s*(?:include(?:If)?|pager|difftool|mergetool|browser|man)\b|"
    r"(?:diff|merge|browser|man)(?:tool)?\.[^\s=]*\.path\s*=|"
    r"=['\"\s]*!)"
)

RISKY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "curl_pipe_shell",
        re.compile(
            r"(?i)\b(?:curl|wget|invoke-webrequest)\b[^\n|]*\|\s*(?:env\s+)?(?:bash|zsh|dash|fish|sh|python3?|perl|ruby|node|iex|invoke-expression)\b"
        ),
    ),
    (
        "eval_or_exec",
        re.compile(
            r"(?:\b(?:eval|exec)\s*\(|(?:^|[;&|]\s*)eval\s+|\bos\.system\s*\(|\bsubprocess\.[^\n]*\bshell\s*=\s*True\b)"
        ),
    ),
    (
        "base64_decode",
        re.compile(r"(?:\bbase64\s+(?:-d|--decode)\b|\bb64decode\s*\()"),
    ),
    (
        "agent_config_mutation",
        re.compile(
            r"(?:\b(?:AGENTS\.md|CLAUDE\.md|MEMORY\.md|settings\.json)\b|(?:\.claude|\.gemini|\.copilot)/|\.git/hooks)"
        ),
    ),
    (
        "index_or_proxy_override",
        re.compile(
            r"(?:--(?:extra-)?index-url\b|\b(?:PIP_INDEX_URL|UV_INDEX|OPENAI_BASE_URL|ANTHROPIC_BASE_URL|HTTP_PROXY|HTTPS_PROXY)\b)"
        ),
    ),
    (
        "sensitive_path_access",
        re.compile(r"(?:\.ssh/|id_(?:rsa|ed25519)\b|\.aws/credentials|\.netrc\b|/etc/shadow\b)"),
    ),
)


def _is_unsafe_char(ch: str) -> bool:
    code = ord(ch)
    cat = unicodedata.category(ch)
    return (cat == "Cc" and ch not in "\n\r\t") or cat == "Cf" or 0xFE00 <= code <= 0xFE0F or 0xE0100 <= code <= 0xE01EF


def _unsafe_char_kind(ch: str) -> str:
    code = ord(ch)
    if unicodedata.category(ch) == "Cc":
        return "ascii_control" if code < 128 else "c1_control"
    if 0xE0000 <= code <= 0xE007F:
        return "unicode_tag"
    if 0xFE00 <= code <= 0xFE0F or 0xE0100 <= code <= 0xE01EF:
        return "variation_selector"
    return "bidi_or_format"


def _expected_py_source(pyc_path: Path) -> Path:
    if pyc_path.parent.name == "__pycache__":
        module_name = pyc_path.stem.split(".", 1)[0]
        return pyc_path.parent.parent / f"{module_name}.py"
    return pyc_path.with_suffix(".py")


def _sanitize_output(value: str) -> str:
    return "".join(f"\\u{ord(ch):04x}" if (_is_unsafe_char(ch) or ch in "\r\n") else ch for ch in value)


def _sanitize_snippet(line: str) -> str:
    return _sanitize_output(line.strip())[:MAX_SNIPPET_CHARS]


def _line_has_git_continuation(line: str) -> bool:
    """Return True iff a Git config line ends with an unescaped continuation backslash outside comments."""
    in_quote = False
    escaped = False
    for ch in line:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == '"':
            in_quote = not in_quote
        elif not in_quote and ch in {"#", ";"}:
            return False
    return escaped


def _unfold_git_config_lines(text: str) -> list[tuple[int, str]]:
    """Join valid backslash-continued Git config lines while keeping each entry's starting 1-based line number."""
    logical: list[tuple[int, str]] = []
    raw_lines = LINE_SPLIT_RE.split(text)
    idx = 0
    while idx < len(raw_lines):
        start_no = idx + 1
        buf = raw_lines[idx]
        while _line_has_git_continuation(buf) and idx + 1 < len(raw_lines):
            idx += 1
            buf = buf[:-1] + raw_lines[idx]
        logical.append((start_no, buf))
        idx += 1
    return logical


def _scan_text_file(
    rel: str,
    text: str,
    unsafe_chars: list[dict[str, Any]],
    risky_patterns: list[dict[str, Any]],
    *,
    check_unsafe_chars: bool = True,
    extra_rules: tuple[tuple[str, re.Pattern[str]], ...] = (),
    unfold_extra_rules: bool = False,
) -> None:
    char_hits = 0
    seen_hits: set[tuple[int, str]] = set()
    rules = (*RISKY_RULES, *extra_rules)
    for line_no, line in enumerate(LINE_SPLIT_RE.split(text), start=1):
        if check_unsafe_chars and char_hits < MAX_UNSAFE_CHARS_PER_FILE:
            for col_no, ch in enumerate(line, start=1):
                if _is_unsafe_char(ch):
                    unsafe_chars.append(
                        {
                            "path": rel,
                            "line": line_no,
                            "col": col_no,
                            "codepoint": f"U+{ord(ch):04X}",
                            "kind": _unsafe_char_kind(ch),
                        }
                    )
                    char_hits += 1
                    if char_hits >= MAX_UNSAFE_CHARS_PER_FILE:
                        break
        for rule_name, pattern in rules:
            if pattern.search(line):
                seen_hits.add((line_no, rule_name))
                risky_patterns.append(
                    {
                        "path": rel,
                        "line": line_no,
                        "rule": rule_name,
                        "snippet": _sanitize_snippet(line),
                    }
                )
    if unfold_extra_rules and extra_rules:
        for line_no, line in _unfold_git_config_lines(text):
            for rule_name, pattern in extra_rules:
                if (line_no, rule_name) not in seen_hits and pattern.search(line):
                    seen_hits.add((line_no, rule_name))
                    risky_patterns.append(
                        {
                            "path": rel,
                            "line": line_no,
                            "rule": rule_name,
                            "snippet": _sanitize_snippet(line),
                        }
                    )


def _is_within_root(path: Path, root_resolved: Path) -> bool:
    return path == root_resolved or root_resolved in path.parents


def _has_git_component(parts: tuple[str, ...]) -> bool:
    return any(part.lower() == ".git" for part in parts)


def _is_within_top_git(path: Path, root_resolved: Path) -> bool:
    if not _is_within_root(path, root_resolved) or path == root_resolved:
        return False
    return path.relative_to(root_resolved).parts[0].lower() == ".git"


def _check_symlink(entry: Path, rel_path: Path, root_resolved: Path) -> dict[str, Any] | None:
    """Return an escape, loop, or .git-target finding using POSIX component-by-component symlink resolution."""
    raw_target = entry.readlink()
    rel = rel_path.as_posix()
    if raw_target.is_absolute():
        current = Path(raw_target.anchor)
        pending = list(raw_target.parts[1:])
    else:
        current = root_resolved / rel_path.parent
        pending = list(raw_target.parts)

    hops = 1
    seen_states: set[tuple[Path, tuple[str, ...]]] = {(root_resolved / rel_path, tuple(pending))}

    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            was_inside = _is_within_root(current, root_resolved)
            current = current.parent
            if was_inside and not _is_within_root(current, root_resolved):
                return {"path": rel, "target": str(raw_target), "resolved": str(current)}
            continue

        nxt = current / part
        if _is_within_top_git(nxt, root_resolved):
            return {"path": rel, "target": str(raw_target), "resolved": f"{nxt} (inside .git)"}
        try:
            st = nxt.lstat()
        except OSError:
            current = nxt
            continue

        if stat.S_ISLNK(st.st_mode):
            if not _is_within_root(nxt, root_resolved):
                return {"path": rel, "target": str(raw_target), "resolved": str(nxt)}
            hops += 1
            if hops > MAX_SYMLINK_HOPS:
                return {"path": rel, "target": str(raw_target), "resolved": "symlink_depth_exceeded"}
            hop_target = nxt.readlink()
            if hop_target.is_absolute():
                current = Path(hop_target.anchor)
                new_pending = [*hop_target.parts[1:], *pending]
            else:
                new_pending = [*hop_target.parts, *pending]
            state = (nxt, tuple(new_pending))
            if state in seen_states:
                return {"path": rel, "target": str(raw_target), "resolved": "symlink_loop"}
            seen_states.add(state)
            pending = new_pending
            continue

        current = nxt

    if not _is_within_root(current, root_resolved):
        return {"path": rel, "target": str(raw_target), "resolved": str(current)}
    if _is_within_top_git(current, root_resolved):
        return {"path": rel, "target": str(raw_target), "resolved": f"{current} (inside .git)"}

    try:
        posix_final = (root_resolved / rel_path).resolve(strict=False)
    except (RuntimeError, OSError) as err:
        return {"path": rel, "target": str(raw_target), "resolved": f"unresolvable ({type(err).__name__})"}
    if not _is_within_root(posix_final, root_resolved):
        return {"path": rel, "target": str(raw_target), "resolved": str(posix_final)}
    if _is_within_top_git(posix_final, root_resolved):
        return {"path": rel, "target": str(raw_target), "resolved": f"{posix_final} (inside .git)"}
    return None


def _decode_text_bytes(raw_bytes: bytes) -> str | None:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
            try:
                return raw_bytes.decode("utf-16")
            except UnicodeDecodeError:
                return None
        return None


def _read_head_tail_text(entry: Path, size: int) -> str:
    with entry.open("rb") as handle:
        head = handle.read(HEAD_TAIL_BYTES)
        tail_offset = max(HEAD_TAIL_BYTES, size - HEAD_TAIL_BYTES)
        handle.seek(tail_offset)
        tail = handle.read(HEAD_TAIL_BYTES)
    head_text = head.decode("utf-8", errors="replace")
    tail_text = tail.decode("utf-8", errors="replace")
    return f"{head_text}\n{tail_text}"


def _inspect_regular_file(
    entry: Path,
    rel: str,
    st: os.stat_result,
    unsafe_chars: list[dict[str, Any]],
    risky_patterns: list[dict[str, Any]],
    unscanned_or_truncated: list[dict[str, Any]],
    *,
    extra_rules: tuple[tuple[str, re.Pattern[str]], ...] = (),
    unfold_extra_rules: bool = False,
) -> bool:
    """Scan one regular file; return True when fully decoded and scanned."""
    if st.st_size > MAX_FILE_BYTES:
        unscanned_or_truncated.append(
            {
                "path": rel,
                "reason": f"exceeds {MAX_FILE_BYTES} bytes ({st.st_size} bytes); scanned head/tail chunks only",
            }
        )
        try:
            chunk_text = _read_head_tail_text(entry, st.st_size)
        except OSError as err:
            unscanned_or_truncated.append({"path": rel, "reason": f"unreadable file ({type(err).__name__})"})
            return False
        _scan_text_file(
            rel,
            chunk_text,
            unsafe_chars,
            risky_patterns,
            check_unsafe_chars=False,
            extra_rules=extra_rules,
            unfold_extra_rules=unfold_extra_rules,
        )
        return False

    try:
        raw_bytes = entry.read_bytes()
    except OSError as err:
        unscanned_or_truncated.append({"path": rel, "reason": f"unreadable file ({type(err).__name__})"})
        return False
    text = _decode_text_bytes(raw_bytes)
    if text is None:
        unscanned_or_truncated.append(
            {
                "path": rel,
                "reason": "non-UTF-8 or binary content requires manual inspection",
            }
        )
        fallback = raw_bytes.decode("utf-8", errors="replace")
        _scan_text_file(
            rel,
            fallback,
            unsafe_chars,
            risky_patterns,
            check_unsafe_chars=False,
            extra_rules=extra_rules,
            unfold_extra_rules=unfold_extra_rules,
        )
        return False

    _scan_text_file(
        rel,
        text,
        unsafe_chars,
        risky_patterns,
        extra_rules=extra_rules,
        unfold_extra_rules=unfold_extra_rules,
    )
    return True


def _flag_git_symlink(
    entry: Path,
    rel_path: Path,
    root_resolved: Path,
    symlinks_escaping_root: list[dict[str, Any]],
    risky_patterns: list[dict[str, Any]],
) -> None:
    if finding := _check_symlink(entry, rel_path, root_resolved):
        symlinks_escaping_root.append(finding)
        return
    risky_patterns.append(
        {
            "path": rel_path.as_posix(),
            "line": 0,
            "rule": "git_metadata_symlink",
            "snippet": _sanitize_snippet(f"-> {entry.readlink()}"),
        }
    )


def _looks_like_gitdir(directory: Path) -> bool:
    try:
        names = {child.name.lower() for child in directory.iterdir()}
    except OSError:
        return False
    return "head" in names or "config" in names


def _audit_top_git_dir(
    git_dir: Path,
    root: Path,
    root_resolved: Path,
    symlinks_escaping_root: list[dict[str, Any]],
    executables_outside_scripts: list[dict[str, Any]],
    unsafe_chars: list[dict[str, Any]],
    risky_patterns: list[dict[str, Any]],
    unscanned_or_truncated: list[dict[str, Any]],
) -> int:
    """Audit executable hooks, config, and submodule metadata inside a .git directory without scanning packfiles."""
    scanned = 0
    try:
        git_entries = sorted(git_dir.iterdir(), key=lambda p: p.name)
    except OSError as err:
        unscanned_or_truncated.append(
            {"path": git_dir.relative_to(root).as_posix(), "reason": f"unreadable git directory ({type(err).__name__})"}
        )
        return 0

    for item in git_entries:
        name_low = item.name.lower()
        if name_low not in {"config", "config.worktree", "hooks", "modules"}:
            continue
        item_rel_path = item.relative_to(root)
        item_rel = item_rel_path.as_posix()
        try:
            item_st = item.lstat()
        except OSError as err:
            unscanned_or_truncated.append(
                {"path": item_rel, "reason": f"unreadable git metadata ({type(err).__name__})"}
            )
            continue

        if name_low in {"config", "config.worktree"}:
            if stat.S_ISLNK(item_st.st_mode):
                _flag_git_symlink(item, item_rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
            elif stat.S_ISREG(item_st.st_mode):
                if _inspect_regular_file(
                    item,
                    item_rel,
                    item_st,
                    unsafe_chars,
                    risky_patterns,
                    unscanned_or_truncated,
                    extra_rules=(("git_config_exec", GIT_CONFIG_EXEC_RE),),
                    unfold_extra_rules=True,
                ):
                    scanned += 1
            else:
                unscanned_or_truncated.append({"path": item_rel, "reason": "non-regular git config entry"})
            continue

        if name_low == "hooks":
            if stat.S_ISLNK(item_st.st_mode):
                _flag_git_symlink(item, item_rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
            elif stat.S_ISDIR(item_st.st_mode):
                try:
                    hook_entries = sorted(item.iterdir(), key=lambda p: p.name)
                except OSError as err:
                    unscanned_or_truncated.append(
                        {"path": item_rel, "reason": f"unreadable git hooks directory ({type(err).__name__})"}
                    )
                    hook_entries = []
                for hook in hook_entries:
                    hook_rel_path = hook.relative_to(root)
                    hook_rel = hook_rel_path.as_posix()
                    try:
                        hst = hook.lstat()
                    except OSError as err:
                        unscanned_or_truncated.append(
                            {"path": hook_rel, "reason": f"unreadable git hook ({type(err).__name__})"}
                        )
                        continue
                    if stat.S_ISLNK(hst.st_mode):
                        _flag_git_symlink(hook, hook_rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
                        continue
                    if not stat.S_ISREG(hst.st_mode):
                        unscanned_or_truncated.append({"path": hook_rel, "reason": "non-regular entry in .git/hooks"})
                        continue
                    if hook.name.lower().endswith(".sample"):
                        continue
                    executables_outside_scripts.append({"path": hook_rel, "mode": oct(stat.S_IMODE(hst.st_mode))})
                    if _inspect_regular_file(
                        hook,
                        hook_rel,
                        hst,
                        unsafe_chars,
                        risky_patterns,
                        unscanned_or_truncated,
                    ):
                        scanned += 1
            else:
                unscanned_or_truncated.append({"path": item_rel, "reason": "non-directory .git/hooks entry"})
            continue

        # Remaining matched entry is the submodule metadata directory.
        if stat.S_ISLNK(item_st.st_mode):
            _flag_git_symlink(item, item_rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
        elif stat.S_ISDIR(item_st.st_mode):
            mod_stack = [item]
            while mod_stack:
                mod_cur = mod_stack.pop()
                at_modules_root = mod_cur == item
                cur_is_gitdir = not at_modules_root and _looks_like_gitdir(mod_cur)
                try:
                    mod_entries = sorted(mod_cur.iterdir(), key=lambda p: p.name)
                except OSError as err:
                    unscanned_or_truncated.append(
                        {
                            "path": mod_cur.relative_to(root).as_posix(),
                            "reason": f"unreadable git modules directory ({type(err).__name__})",
                        }
                    )
                    continue
                for entry in mod_entries:
                    entry_rel_path = entry.relative_to(root)
                    try:
                        est = entry.lstat()
                    except OSError as err:
                        unscanned_or_truncated.append(
                            {
                                "path": entry_rel_path.as_posix(),
                                "reason": f"unreadable git modules entry ({type(err).__name__})",
                            }
                        )
                        continue
                    if stat.S_ISLNK(est.st_mode):
                        _flag_git_symlink(entry, entry_rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
                    elif stat.S_ISDIR(est.st_mode):
                        entry_low = entry.name.lower()
                        if not at_modules_root and entry_low in {"hooks", "modules"}:
                            continue
                        scanned += _audit_top_git_dir(
                            entry,
                            root,
                            root_resolved,
                            symlinks_escaping_root,
                            executables_outside_scripts,
                            unsafe_chars,
                            risky_patterns,
                            unscanned_or_truncated,
                        )
                        if not (cur_is_gitdir and entry_low in {"objects", "logs", "refs", "info"}):
                            mod_stack.append(entry)
                    elif not stat.S_ISREG(est.st_mode):
                        unscanned_or_truncated.append(
                            {"path": entry_rel_path.as_posix(), "reason": "non-regular entry in .git/modules"}
                        )
        else:
            unscanned_or_truncated.append({"path": item_rel, "reason": "non-directory .git/modules entry"})
    return scanned


def audit_directory(root: Path) -> dict[str, Any]:
    """Statically inspect all entries under root without following symlinks or executing code."""
    root_resolved = root.resolve()
    symlinks_escaping_root: list[dict[str, Any]] = []
    executables_outside_scripts: list[dict[str, Any]] = []
    orphan_pyc: list[dict[str, Any]] = []
    unsafe_chars: list[dict[str, Any]] = []
    risky_patterns: list[dict[str, Any]] = []
    unscanned_or_truncated: list[dict[str, Any]] = []
    files_scanned = 0

    stack = [root]
    while stack:
        current = stack.pop()
        entries = sorted(current.iterdir(), key=lambda p: p.name)
        for entry in entries:
            rel_path = entry.relative_to(root)
            rel = rel_path.as_posix()
            st = entry.lstat()
            mode = st.st_mode

            if stat.S_ISLNK(mode):
                if _has_git_component(rel_path.parts):
                    _flag_git_symlink(entry, rel_path, root_resolved, symlinks_escaping_root, risky_patterns)
                elif finding := _check_symlink(entry, rel_path, root_resolved):
                    symlinks_escaping_root.append(finding)
                continue

            if stat.S_ISDIR(mode):
                if current == root and entry.name.lower() == ".git":
                    files_scanned += _audit_top_git_dir(
                        entry,
                        root,
                        root_resolved,
                        symlinks_escaping_root,
                        executables_outside_scripts,
                        unsafe_chars,
                        risky_patterns,
                        unscanned_or_truncated,
                    )
                else:
                    stack.append(entry)
                continue

            if not stat.S_ISREG(mode):
                unscanned_or_truncated.append({"path": rel, "reason": "non-regular filesystem entry"})
                continue

            parent_parts = rel_path.parts[:-1]
            in_git_hooks = (
                bool(parent_parts) and parent_parts[-1].lower() == "hooks" and _has_git_component(parent_parts)
            )
            if (in_git_hooks and not entry.name.lower().endswith(".sample")) or (
                mode & 0o111 and "scripts" not in parent_parts
            ):
                executables_outside_scripts.append({"path": rel, "mode": oct(stat.S_IMODE(mode))})

            if entry.suffix.lower() in {".pyc", ".pyo"}:
                expected = _expected_py_source(entry)
                try:
                    expected_st = expected.lstat()
                    has_source = stat.S_ISREG(expected_st.st_mode)
                except OSError:
                    has_source = False
                if not has_source:
                    orphan_pyc.append(
                        {
                            "path": rel,
                            "expected_source": expected.relative_to(root).as_posix()
                            if root in expected.parents or expected.parent == root
                            else str(expected),
                        }
                    )
                else:
                    unscanned_or_truncated.append(
                        {
                            "path": rel,
                            "reason": "compiled Python bytecode (.pyc/.pyo) is unverified binary code and can diverge from source",
                        }
                    )
                continue

            if entry.name.lower() == ".git":
                risky_patterns.append(
                    {
                        "path": rel,
                        "line": 0,
                        "rule": "gitdir_pointer_file",
                        "snippet": "regular .git file can redirect gitdir/hooks outside root",
                    }
                )

            is_git_cfg = entry.name.lower() in {"config", "config.worktree"} and _has_git_component(parent_parts)
            extra_rules = (("git_config_exec", GIT_CONFIG_EXEC_RE),) if is_git_cfg else ()
            if _inspect_regular_file(
                entry,
                rel,
                st,
                unsafe_chars,
                risky_patterns,
                unscanned_or_truncated,
                extra_rules=extra_rules,
                unfold_extra_rules=is_git_cfg,
            ):
                files_scanned += 1

    findings = {
        "symlinks_escaping_root": symlinks_escaping_root,
        "executables_outside_scripts": executables_outside_scripts,
        "orphan_pyc": orphan_pyc,
        "unsafe_chars": unsafe_chars,
        "risky_patterns": risky_patterns,
        "unscanned_or_truncated": unscanned_or_truncated,
    }
    finding_count = sum(len(items) for items in findings.values())
    return {
        "root": str(root_resolved),
        "files_scanned": files_scanned,
        "skipped_binary_or_large": [item["path"] for item in unscanned_or_truncated],
        "finding_count": finding_count,
        "findings": findings,
    }


def _format_text(report: dict[str, Any]) -> str:
    lines = [
        f"Static skill audit: {_sanitize_output(str(report['root']))}",
        f"Files scanned: {report['files_scanned']} | Findings: {report['finding_count']}",
    ]
    findings = report["findings"]
    for category, items in findings.items():
        if not items:
            continue
        lines.append(f"\n[{category}] ({len(items)})")
        for item in items:
            detail = " ".join(f"{k}={_sanitize_output(str(v))}" for k, v in item.items() if k != "path")
            lines.append(f"  - {_sanitize_output(str(item['path']))}: {detail}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, run read-only static audit, and emit findings."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument("root", type=Path, help="Untrusted skill directory to audit statically")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit structured JSON output")
    args = parser.parse_args(argv)
    if not args.root.exists() or not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")
    try:
        report = audit_directory(args.root)
    except OSError as error:
        if args.as_json:
            sys.stderr.write(json.dumps({"error": str(error)}) + "\n")
        else:
            sys.stderr.write(f"Error: {_sanitize_output(str(error))}\n")
        return 1
    if args.as_json:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        sys.stdout.write(_format_text(report))
    return 1 if report["finding_count"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
