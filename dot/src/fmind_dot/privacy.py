"""Workstation privacy scanner for emails, SSH comments, local identifiers, and .age integrity."""

from __future__ import annotations

import argparse
import os
import re
import socket
import stat
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

from fmind_dot.config import yaml_error_location
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner, diagnostic_line, run_parallel
from fmind_dot.reporting import display_path, write_json

if TYPE_CHECKING:
    from fmind_dot.state import State

PRIVACY_SCHEMA = "dot.privacy/v1"
_GIT_TIMEOUT_SECONDS = 30.0
_PRIVACY_CONCURRENCY = 8

ALLOWED_EMAIL_DOMAINS = {
    "fmind.dev",
    "fmind.ai",
    "github.com",
    "users.noreply.github.com",
    "example.iam.gserviceaccount.com",
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
}
ALLOWED_EMAIL_SUFFIXES = (
    ".fmind.dev",
    ".fmind.ai",
    ".example.com",
    ".example.org",
    ".example.net",
    ".example.edu",
    ".example",
    ".test",
    ".invalid",
    ".localhost",
)
EMAIL_PATTERN = re.compile(
    r"(?:(?<=\\n)|(?<=\\r)|(?<=\\t)|(?<![A-Za-z0-9._%+\\-]))"
    r"([A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}))\b"
)
# SSH key comments default to user@hostname, which EMAIL_PATTERN misses without a dotted domain.
SSH_KEY_COMMENT_PATTERN = re.compile(
    r"(?:ssh-(?:ed25519|rsa|dss)|ecdsa-sha2-nistp\d+|sk-(?:ssh-ed25519|ecdsa-sha2-nistp256)@openssh\.com)"
    r"[ \t]+AAAA[A-Za-z0-9+/]*=*[ \t]+([^\s\"'\\]+)"
)
PRIVACY_SKIP_PATHS = {
    "dot/uv.lock",
    "dot_config/mise/mise.lock",
    "dot_config/nvim/lazy-lock.json",
    "mise.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "uv.lock",
}
PRIVACY_SKIP_PREFIXES = (".mise/locks/", "dot_config/mise/locks/")
SAFE_HOST_TOKENS = {
    "chezmoi",
    "courses",
    "customers",
    "debian",
    "default",
    "example",
    "fmind",
    "github",
    "google",
    "hurier",
    "local",
    "localhost",
    "mederic",
    "personal",
    "ubuntu",
}
_EMAIL_HINT = "use fmind.dev, fmind.ai, or RFC 2606 domains (@example.com, @example.test)"
_SSH_HINT = "may name a machine or account; use an approved email such as git-signing@fmind.dev"
_HOST_HINT = (
    "from untracked host config; remove it, or list an already-public name"
    " under privacy.allowed_tokens in ~/.config/dot.yaml"
)


def _is_allowed_email_domain(domain: str) -> bool:
    lowered = domain.lower().strip(".")
    # The leading dot also accepts bare reserved names such as `test` or `localhost`.
    return lowered in ALLOWED_EMAIL_DOMAINS or f".{lowered}".endswith(ALLOWED_EMAIL_SUFFIXES)


def _privacy_error(target: Path, why: str) -> ValueError:
    return ValueError(f"{target}: cannot load local privacy tokens; {why}")


def _listdir(directory: Path) -> list[Path] | None:
    try:
        return sorted(directory.iterdir())
    except FileNotFoundError:
        return None
    except OSError as error:
        raise _privacy_error(directory, f"fix permissions ({error.__class__.__name__})") from error


def _load_dot_yaml_mapping(dot_yaml: Path, *, required: bool = False) -> dict[str, Any] | None:
    try:
        raw_text = dot_yaml.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        if required:
            raise _privacy_error(dot_yaml, "file not found") from error
        return None
    except (OSError, UnicodeError) as error:
        raise _privacy_error(dot_yaml, f"fix or remove the file ({error.__class__.__name__})") from error
    import yaml

    try:
        config = yaml.safe_load(raw_text)
    except yaml.YAMLError as error:
        # Never format yaml.YAMLError directly: PyYAML embeds raw lines from untracked dot.yaml.
        loc = yaml_error_location(error) or "invalid YAML"
        raise _privacy_error(dot_yaml, f"fix or remove the file ({loc})") from error
    except RecursionError as error:
        raise _privacy_error(dot_yaml, f"fix or remove the file ({error.__class__.__name__})") from error
    if config is not None and not isinstance(config, dict):
        raise _privacy_error(dot_yaml, "expected a YAML mapping")
    return config


def _workstation_tokens(
    home: Path,
    *,
    include_hostname: bool = False,
    config_path: Path | None = None,
) -> set[str]:
    """Extract non-public employer/workstation identifiers from untracked local config."""
    tokens, cfg_dir = set(), home / ".config"
    dot_files = [p for p in _listdir(cfg_dir) or () if p.name.startswith("dot.") and p.suffix == ".yaml"]
    dot_paths: list[tuple[Path, bool]] = [
        (cfg_dir / "dot.yaml", False),
        *((p, False) for p in dot_files if p.name != "dot.yaml"),
    ]
    raw_explicit: Path | None = None
    if config_path is not None:
        raw_explicit = config_path
    elif (env := os.environ.get("DOT_CONFIG_PATH", "").strip()) and home.resolve() == Path.home().resolve():
        raw_explicit = Path(env)
    if raw_explicit is not None:
        try:
            explicit_path = raw_explicit.expanduser()
        except RuntimeError as error:
            raise _privacy_error(raw_explicit, "invalid home prefix") from error
        dot_paths.append((explicit_path, True))

    required_by_path: dict[Path, bool] = {}
    for path, req in dot_paths:
        required_by_path[path] = required_by_path.get(path, False) or req

    configs = [
        cfg for path, req in required_by_path.items() if (cfg := _load_dot_yaml_mapping(path, required=req)) is not None
    ]
    safe = set(SAFE_HOST_TOKENS)
    for cfg in configs:
        if isinstance(priv := cfg.get("privacy"), dict) and isinstance(al := priv.get("allowed_tokens"), list):
            safe |= {e.strip().lower() for e in al if isinstance(e, str)}

    def _add(candidate: str) -> None:
        if len(cleaned := candidate.strip().lower()) >= 4 and cleaned not in safe:
            tokens.add(cleaned)

    for cfg in configs:
        for sec in (cfg.get("auth") or {}).values() if isinstance(cfg.get("auth"), dict) else ():
            if isinstance(sec, dict) and isinstance(proj := sec.get("project"), str):
                _add(proj)
        for s, k in (("pull", "directories"), ("trust", "github_owners"), ("trust", "agy_projects")):
            if isinstance(sec := cfg.get(s), dict) and isinstance(vals := sec.get(k), list):
                for val in (v for v in vals if isinstance(v, str)):
                    if k == "directories":
                        _add(Path(val.rstrip("/")).name)
                    elif k == "agy_projects":
                        parts = [
                            p
                            for p in Path(val.rstrip("/")).parts
                            if p not in {"/", "~"} and not any(c in p for c in "*?[")
                        ]
                        if parts:
                            _add(parts[-1])
                    else:
                        _add(val)

    for entry in _listdir(cfg_dir) or ():
        if entry.name.startswith("gws-"):
            _add(entry.name.removeprefix("gws-"))

    git_configs: list[Path] = [
        p
        for p in _listdir(home / ".config/git") or ()
        if p.name not in {"allowed_signers", "colors.gitconfig", "personal.gitconfig", "theme.gitconfig"}
    ]
    git_configs.append(home / ".gitconfig")

    for path in git_configs:
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                continue
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError) as error:
            raise _privacy_error(path, f"fix or remove the file ({error.__class__.__name__})") from error
        if path.name.startswith("config."):
            _add(path.name.removeprefix("config."))
        for match in EMAIL_PATTERN.finditer(text):
            if not _is_allowed_email_domain(dom := match.group(2)):
                for item in (match.group(1), dom, *dom.split(".")[:-1]):
                    _add(item)
        for user_match in re.finditer(r"^\s*user\s*=\s*(.+?)\s*$", text, re.MULTILINE):
            _add(user_match.group(1).strip().strip("\"'"))

    if include_hostname:
        _add(socket.gethostname().split(".")[0])
    return tokens


_NOT_A_GIT_REPO = "not a git repository (or any"


def _run_git(runner: Runner, root: Path, *args: str) -> CommandResult:
    return runner.run(["git", "-C", str(root), *args], env={"LC_ALL": "C"}, timeout=_GIT_TIMEOUT_SECONDS, check=False)


def _git_error(action: str, detail: str) -> str:
    return f"git {action} failed ({detail}); fix repository state before publishing"


def _git_detail(res: CommandResult) -> str:
    return diagnostic_line(res.stderr) or f"exit {res.returncode}"


def _detect_git_worktree(runner: Runner, root: Path) -> tuple[bool, str | None]:
    """Return ``(in_worktree, error)``; fail closed if any ancestor ``.git`` exists or git fails."""
    try:
        res = _run_git(runner, root, "rev-parse", "--is-inside-work-tree")
    except (DotError, OSError) as error:
        return False, _git_error("rev-parse", error.__class__.__name__)
    if res.returncode == 0:
        return res.stdout.strip() == "true", None
    resolved = root.resolve()
    if (
        res.returncode == 128
        and _NOT_A_GIT_REPO in res.stderr.lower()
        and not any(os.path.lexists(parent / ".git") for parent in (resolved, *resolved.parents))
    ):
        return False, None
    return False, _git_error("rev-parse", _git_detail(res))


def _has_git_head(runner: Runner, root: Path) -> tuple[bool, str | None]:
    try:
        res = _run_git(runner, root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    except (DotError, OSError) as error:
        return False, _git_error("rev-parse HEAD", error.__class__.__name__)
    if res.returncode == 0:
        return True, None
    if res.returncode != 1 or res.stderr.strip():
        return False, _git_error("rev-parse HEAD", _git_detail(res))
    try:
        sym = _run_git(runner, root, "symbolic-ref", "--quiet", "HEAD")
        if sym.returncode != 0 or not (ref := sym.stdout.strip()):
            return False, _git_error("rev-parse HEAD", _git_detail(sym))
        show_ref = _run_git(runner, root, "show-ref", "--verify", "--quiet", ref)
        if show_ref.returncode != 1 or show_ref.stderr.strip():
            detail = (
                "corrupt ref" if show_ref.returncode == 0 and not show_ref.stderr.strip() else _git_detail(show_ref)
            )
            return False, _git_error("rev-parse HEAD", detail)
        ref_path = _run_git(runner, root, "rev-parse", "--git-path", ref)
        if ref_path.returncode != 0 or not (rel_ref := ref_path.stdout.strip()):
            return False, _git_error("rev-parse HEAD", _git_detail(ref_path))
    except (DotError, OSError) as error:
        return False, _git_error("rev-parse HEAD", error.__class__.__name__)
    candidate = Path(rel_ref)
    full_ref = candidate if candidate.is_absolute() else root / candidate
    if os.path.lexists(full_ref):
        return False, _git_error("rev-parse HEAD", "corrupt ref")
    return False, None


def _walk_non_git_files(root: Path) -> tuple[list[str], list[str]]:
    relatives: list[str] = []
    errors: list[str] = []

    def _on_error(error: OSError) -> None:
        where = error.filename or str(root)
        errors.append(f"{where}: unreadable directory ({error.__class__.__name__})")

    for current, dirs, files in os.walk(root, onerror=_on_error):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        current_path = Path(current)
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink() and not name.endswith(".age"):
                continue
            relatives.append(path.relative_to(root).as_posix())
    return relatives, errors


def _scan_git_commits(runner: Runner, root: Path, token_pat: re.Pattern[str] | None) -> list[str]:
    has_head, head_err = _has_git_head(runner, root)
    if head_err is not None:
        return [head_err]
    if not has_head:
        return []
    try:
        log_res = _run_git(runner, root, "log", "HEAD", "--format=%h%x09%ae%x09%ce")
    except (DotError, OSError) as error:
        return [_git_error("log", error.__class__.__name__)]
    if log_res.returncode != 0:
        return [_git_error("log", _git_detail(log_res))]
    findings: list[str] = []
    for line in log_res.stdout.splitlines():
        if len(parts := line.split("\t")) != 3:
            continue
        pre = f"git commit {parts[0]}"
        for role, email in (("author", parts[1]), ("committer", parts[2])):
            dom = email.partition("@")[2]
            if not dom or not _is_allowed_email_domain(dom):
                findings.append(f"{pre}: unapproved {role} email {email!r}; use fmind.dev, fmind.ai, or github.com")
            elif token_pat is not None and (hit := token_pat.search(email)) is not None:
                findings.append(f"{pre}: {role} email contains local workstation identifier {hit.group(0)!r}")
    return findings


def _list_target_files(runner: Runner, root: Path) -> tuple[bool, list[str], list[str]]:
    has_git, git_err = _detect_git_worktree(runner, root)
    if git_err is not None:
        return False, [], [git_err]
    if not has_git:
        relatives, walk_errors = _walk_non_git_files(root)
        return False, relatives, walk_errors
    try:
        listed = _run_git(runner, root, "ls-files", "-coz", "--exclude-standard")
    except (DotError, OSError) as error:
        return True, [], [_git_error("ls-files", error.__class__.__name__)]
    if listed.returncode != 0:
        return True, [], [_git_error("ls-files", _git_detail(listed))]
    return True, [item for item in listed.stdout.split("\0") if item], []


def _compile_token_pattern(
    home: Path,
    *,
    include_hostname: bool,
    config_path: Path | None,
) -> tuple[re.Pattern[str] | None, list[str]]:
    try:
        tokens = _workstation_tokens(home, include_hostname=include_hostname, config_path=config_path)
    except ValueError as error:
        return None, [str(error)]
    if not tokens:
        return None, []
    escaped = "|".join(re.escape(t) for t in sorted(tokens, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9])(?:{escaped})(?![A-Za-z0-9])", re.IGNORECASE), []


_AGE_HEADERS_BYTES = (b"-----BEGIN AGE ENCRYPTED FILE-----\n", b"age-encryption.org/v1\n")


def _scan_text(rel: str, text: str, token_pat: re.Pattern[str] | None) -> list[str]:
    findings: list[str] = []
    bad = [m for m in EMAIL_PATTERN.finditer(text) if not _is_allowed_email_domain(m.group(2))]
    findings.extend(f"{rel}: unapproved email domain {m.group(2)!r} in {m.group(1)!r}; {_EMAIL_HINT}" for m in bad)
    for m in SSH_KEY_COMMENT_PATTERN.finditer(text):
        local, _, dom = (comment := m.group(1)).rpartition("@")
        if not (local and _is_allowed_email_domain(dom)):
            findings.append(f"{rel}: SSH key comment {comment!r} {_SSH_HINT}")
    if token_pat is not None and (hit := token_pat.search(text)) is not None:
        findings.append(f"{rel}: contains local workstation identifier {hit.group(0)!r} {_HOST_HINT}")
    return findings


def _scan_blob_bytes(rel: str, raw: bytes, token_pat: re.Pattern[str] | None) -> list[str]:
    if rel.endswith(".age"):
        if not raw[:64].startswith(_AGE_HEADERS_BYTES):
            return [f"{rel}: .age source is not age-encrypted ciphertext"]
        return []
    if b"\x00" in raw[:8192]:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return _scan_text(rel, text, token_pat)


def _read_exact(stream: IO[bytes], count: int) -> bytes:
    if count <= 0:
        return b""
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _drain_exact(stream: IO[bytes], count: int) -> bool:
    remaining = count
    while remaining > 0:
        chunk = stream.read(min(65536, remaining))
        if not chunk:
            return False
        remaining -= len(chunk)
    return True


def _scan_batch_stream(
    stream: IO[bytes], ordered_shas: list[tuple[str, list[str]]], token_pat: re.Pattern[str] | None
) -> list[str]:
    findings: list[str] = []
    for _, rels in ordered_shas:
        header_line = stream.readline()
        if not header_line.endswith(b"\n"):
            return [*findings, f"{rels[0]}: unreadable staged blob (truncated git cat-file stream)"]
        header = header_line[:-1].decode("utf-8", errors="replace")
        if header.endswith(" missing"):
            findings.extend(f"{rel}: unreadable staged blob (missing)" for rel in rels)
            continue
        parts = header.split()
        if len(parts) != 3 or not parts[2].isdigit():
            return [*findings, f"{rels[0]}: unreadable staged blob (unexpected git cat-file header)"]
        size = int(parts[2])
        all_age = all(rel.endswith(".age") for rel in rels)
        peek_len = min(size, 64 if all_age else 8192)
        head = _read_exact(stream, peek_len)
        if len(head) != peek_len:
            return [*findings, f"{rels[0]}: unreadable staged blob (truncated git cat-file payload)"]
        remaining = size - peek_len
        if all_age or b"\x00" in head:
            if not _drain_exact(stream, remaining) or _read_exact(stream, 1) != b"\n":
                return [*findings, f"{rels[0]}: unreadable staged blob (truncated git cat-file payload)"]
            findings.extend(
                f"{rel}: .age source is not age-encrypted ciphertext"
                for rel in rels
                if rel.endswith(".age") and not head[:64].startswith(_AGE_HEADERS_BYTES)
            )
            continue
        tail = _read_exact(stream, remaining)
        if len(tail) != remaining or _read_exact(stream, 1) != b"\n":
            return [*findings, f"{rels[0]}: unreadable staged blob (truncated git cat-file payload)"]
        raw = head + tail
        for rel in rels:
            findings.extend(_scan_blob_bytes(rel, raw, token_pat))
    return findings


def _scan_staged_blobs(
    runner: Runner, root: Path, blobs: list[tuple[str, str]], token_pat: re.Pattern[str] | None
) -> list[str]:
    if not blobs:
        return []
    grouped: dict[str, list[str]] = {}
    for rel, sha in sorted(blobs):
        grouped.setdefault(sha, []).append(rel)
    ordered_shas = list(grouped.items())
    stdin = "".join(f"{sha}\n" for sha, _ in ordered_shas).encode("ascii")
    try:
        findings, returncode, stderr_bytes = runner.stream_stdout(
            ["git", "-C", str(root), "cat-file", "--batch"],
            lambda stdout: _scan_batch_stream(stdout, ordered_shas, token_pat),
            input_bytes=stdin,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (DotError, OSError) as error:
        return [_git_error("cat-file --batch", error.__class__.__name__)]
    if returncode != 0:
        detail = diagnostic_line(stderr_bytes.decode("utf-8", errors="replace")) or f"exit {returncode}"
        return [_git_error("cat-file --batch", detail)]
    return findings


def _scan_staged_files(runner: Runner, root: Path, token_pat: re.Pattern[str] | None) -> list[str]:
    try:
        diff = _run_git(
            runner,
            root,
            "diff",
            "--cached",
            "--raw",
            "--no-abbrev",
            "--no-renames",
            "--relative",
            "--diff-filter=AMT",
            "-z",
            "--",
            ".",
        )
    except (DotError, OSError) as error:
        return [_git_error("diff --cached", error.__class__.__name__)]
    if diff.returncode != 0:
        return [_git_error("diff --cached", _git_detail(diff))]
    if not diff.stdout:
        return []
    tokens = diff.stdout.split("\0")
    if not diff.stdout.endswith("\0") or len(tokens) % 2 != 1:
        return [_git_error("diff --cached", "unexpected raw diff output")]
    findings: list[str] = []
    blobs: list[tuple[str, str]] = []
    for idx in range(0, len(tokens) - 1, 2):
        meta, rel = tokens[idx], tokens[idx + 1]
        fields = meta[1:].split() if meta.startswith(":") else []
        if not rel or len(fields) != 5 or fields[4] not in {"A", "M", "T"}:
            return [_git_error("diff --cached", "unexpected raw diff output")]
        new_mode, new_sha = fields[1], fields[3]
        if rel in PRIVACY_SKIP_PATHS or rel.startswith(PRIVACY_SKIP_PREFIXES):
            continue
        if new_mode == "120000":
            if rel.endswith(".age"):
                findings.append(f"{rel}: encrypted .age source must not be a symlink")
            continue
        if new_mode not in {"100644", "100755"}:
            if rel.endswith(".age"):
                findings.append(f"{rel}: encrypted .age source must be a regular file")
            continue
        blobs.append((rel, new_sha))
    findings.extend(_scan_staged_blobs(runner, root, blobs, token_pat))
    return findings


def _scan_root(
    root: Path,
    *,
    token_pat: re.Pattern[str] | None,
    token_errors: list[str],
    runner: Runner,
    staged: bool = False,
) -> list[str]:
    findings = list(token_errors)
    if staged:
        has_git, git_err = _detect_git_worktree(runner, root)
        if git_err is not None:
            findings.append(git_err)
            return sorted(set(findings))
        if not has_git:
            findings.append(f"{display_path(str(root))}: --staged requires a Git repository")
            return sorted(set(findings))
        findings.extend(_scan_staged_files(runner, root, token_pat))
        findings.extend(_scan_git_commits(runner, root, token_pat))
        return sorted(set(findings))

    has_git, relatives, list_errors = _list_target_files(runner, root)
    findings.extend(list_errors)

    for rel in sorted(relatives):
        if rel in PRIVACY_SKIP_PATHS or rel.startswith(PRIVACY_SKIP_PREFIXES):
            continue
        path = root / rel
        if rel.endswith(".age"):
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            except OSError as error:
                findings.append(f"{rel}: unreadable .age source ({error.__class__.__name__})")
                continue
            if stat.S_ISLNK(info.st_mode):
                findings.append(f"{rel}: encrypted .age source must not be a symlink")
                continue
            if not stat.S_ISREG(info.st_mode):
                findings.append(f"{rel}: encrypted .age source must be a regular file")
                continue
            try:
                with path.open("rb") as stream:
                    header = stream.read(64)
            except OSError as error:
                findings.append(f"{rel}: unreadable .age source ({error.__class__.__name__})")
                continue
            if not header.startswith(_AGE_HEADERS_BYTES):
                findings.append(f"{rel}: .age source is not age-encrypted ciphertext")
            continue
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            findings.append(f"{rel}: unreadable file ({error.__class__.__name__})")
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        try:
            with path.open("rb") as stream:
                head = stream.read(8192)
                if b"\x00" in head:
                    continue
                raw = head + stream.read()
        except OSError as error:
            findings.append(f"{rel}: unreadable file ({error.__class__.__name__})")
            continue
        findings.extend(_scan_blob_bytes(rel, raw, token_pat))

    if has_git:
        findings.extend(_scan_git_commits(runner, root, token_pat))
    return sorted(set(findings))


def privacy_findings(
    root: Path,
    home: Path | None = None,
    *,
    include_hostname: bool | None = None,
    config_path: Path | None = None,
    runner: Runner | None = None,
    staged: bool = False,
) -> list[str]:
    """Scan non-encrypted repo files and local Git commits for emails, SSH comments, and local tokens."""
    resolved_home = (Path.home() if home is None else home).resolve()
    use_hostname = include_hostname if include_hostname is not None else (home is None)
    token_pat, token_errors = _compile_token_pattern(
        resolved_home,
        include_hostname=use_hostname,
        config_path=config_path,
    )
    return _scan_root(root, token_pat=token_pat, token_errors=token_errors, runner=runner or Runner(), staged=staged)


def _scan_target(
    raw: Path,
    *,
    token_pat: re.Pattern[str] | None,
    token_errors: list[str],
    runner: Runner,
    staged: bool = False,
) -> dict[str, Any]:
    try:
        resolved = raw.expanduser().resolve()
    except (OSError, RuntimeError) as error:
        label = str(raw)
        return {"path": label, "passed": False, "findings": [f"{label}: invalid path ({error.__class__.__name__})"]}
    label = str(resolved)
    if not resolved.is_dir():
        return {"path": label, "passed": False, "findings": [f"{display_path(label)}: directory not found"]}
    findings = _scan_root(resolved, token_pat=token_pat, token_errors=token_errors, runner=runner, staged=staged)
    return {"path": label, "passed": not findings, "findings": findings}


def _privacy(state: State, args: argparse.Namespace) -> None:
    targets: list[Path] = args.paths or [Path()]
    raw_cfg = state.config_argument
    config_path = Path(raw_cfg) if raw_cfg is not None and os.fspath(raw_cfg) != "" else None
    token_pat, token_errors = _compile_token_pattern(
        Path.home().resolve(),
        include_hostname=True,
        config_path=config_path,
    )
    results = run_parallel(
        state.runner,
        lambda target: _scan_target(
            target, token_pat=token_pat, token_errors=token_errors, runner=state.runner, staged=args.staged
        ),
        targets,
        _PRIVACY_CONCURRENCY,
    )
    passed = all(entry["passed"] for entry in results)
    if args.as_json:
        shown = [entry for entry in results if not entry["passed"]] if args.quiet else results
        write_json(state.stdout, {"schema": PRIVACY_SCHEMA, "passed": passed, "targets": shown})
    else:
        for entry in results:
            shown_path = display_path(entry["path"])
            if entry["passed"]:
                if not args.quiet:
                    state.stdout.write(f"✓ {shown_path}: no privacy findings\n")
            else:
                count = len(entry["findings"])
                noun = "finding" if count == 1 else "findings"
                state.stdout.write(f"✗ {shown_path}: {count} privacy {noun}\n")
                for finding in entry["findings"]:
                    state.stdout.write(f"  - {finding}\n")
    if not passed:
        raise SystemExit(1)
