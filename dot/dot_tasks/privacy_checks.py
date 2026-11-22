"""Repository privacy checks for emails, SSH comments, and local workstation identifiers."""

from __future__ import annotations

import os
import re
import socket
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from dot_tasks import ROOT
from fmind_dot.config import yaml_error_location

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
PRIVACY_SKIP_PATHS = {"dot/uv.lock", "dot_config/mise/mise.lock", "dot_config/nvim/lazy-lock.json", "mise.lock"}
PRIVACY_SKIP_PREFIXES = ("dot_config/mise/locks/",)
SAFE_HOST_TOKENS = {
    "chezmoi",
    "courses",
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


def _load_dot_yaml_mapping(dot_yaml: Path) -> dict[str, Any] | None:
    try:
        config = yaml.safe_load(dot_yaml.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except yaml.YAMLError as error:
        # Never format yaml.YAMLError directly: PyYAML embeds raw lines from untracked dot.yaml.
        loc = yaml_error_location(error) or "invalid YAML"
        raise _privacy_error(dot_yaml, f"fix or remove the file ({loc})") from error
    except (OSError, UnicodeError, RecursionError) as error:
        raise _privacy_error(dot_yaml, f"fix or remove the file ({error.__class__.__name__})") from error
    if config is not None and not isinstance(config, dict):
        raise _privacy_error(dot_yaml, "expected a YAML mapping")
    return config


def _workstation_tokens(home: Path, *, include_hostname: bool = False) -> set[str]:
    """Extract non-public employer/workstation identifiers from untracked local config."""
    tokens, cfg_dir = set(), home / ".config"
    dot_files = [p for p in _listdir(cfg_dir) or () if p.name.startswith("dot.") and p.suffix == ".yaml"]
    dot_paths = [cfg_dir / "dot.yaml", *(p for p in dot_files if p.name != "dot.yaml")]
    if (env := os.environ.get("DOT_CONFIG_PATH", "").strip()) and home.resolve() == Path.home().resolve():
        dot_paths.append(Path(env).expanduser())
    configs = [cfg for p in dict.fromkeys(dot_paths) if (cfg := _load_dot_yaml_mapping(p)) is not None]
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
        for s, k in (("pull", "directories"), ("trust", "github_owners")):
            if isinstance(sec := cfg.get(s), dict) and isinstance(vals := sec.get(k), list):
                for val in (v for v in vals if isinstance(v, str)):
                    _add(Path(val.rstrip("/")).name if k == "directories" else val)

    for path in _listdir(home / ".config/git") or ():
        if path.name in {"allowed_signers", "colors.gitconfig", "personal.gitconfig", "theme.gitconfig"}:
            continue
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise _privacy_error(path, f"fix or remove the file ({error.__class__.__name__})") from error
        if path.name.startswith("config."):
            _add(path.name.removeprefix("config."))
        for match in EMAIL_PATTERN.finditer(text):
            if not _is_allowed_email_domain(dom := match.group(2)):
                for item in (match.group(1), dom, *dom.split(".")[:-1]):
                    _add(item)
        for user_match in re.finditer(r"^\s*user\s*=\s*(.+?)\s*$", text, re.MULTILINE):
            _add(user_match.group(1))

    if include_hostname:
        _add(socket.gethostname().split(".")[0])
    return tokens


def privacy_findings(root: Path, home: Path | None = None, *, repo_root: Path = ROOT) -> list[str]:
    """Scan non-encrypted repo files and local Git commits for emails, SSH comments, and local tokens."""
    resolved_home, findings = (Path.home() if home is None else home).resolve(), []
    try:
        tokens = _workstation_tokens(resolved_home, include_hostname=(home is None and root == repo_root))
    except ValueError as error:
        findings.append(str(error))
        tokens = set()
    escaped = "|".join(re.escape(t) for t in sorted(tokens, key=len, reverse=True))
    token_pat = re.compile(rf"(?<![A-Za-z0-9])(?:{escaped})(?![A-Za-z0-9])", re.IGNORECASE) if tokens else None
    if has_git := (root / ".git").exists():
        ls_cmd = ["git", "-C", str(root), "ls-files", "-coz", "--exclude-standard"]
        listed = subprocess.run(ls_cmd, check=True, capture_output=True, timeout=30).stdout  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
        relatives = [item.decode("utf-8", errors="replace") for item in listed.split(b"\0") if item]
    else:
        relatives = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not p.is_symlink()]

    _age_headers = (b"-----BEGIN AGE ENCRYPTED FILE-----\n", b"age-encryption.org/v1\n")
    for rel in sorted(relatives):
        if rel in PRIVACY_SKIP_PATHS or rel.startswith(PRIVACY_SKIP_PREFIXES):
            continue
        path = root / rel
        if rel.endswith(".age"):
            if path.is_symlink():
                findings.append(f"{rel}: encrypted .age source must not be a symlink")
                continue
            if not path.exists():
                continue
            try:
                with path.open("rb") as stream:
                    header = stream.read(64)
            except OSError as error:
                findings.append(f"{rel}: unreadable .age source ({error})")
                continue
            if not header.startswith(_age_headers):
                findings.append(f"{rel}: .age source is not age-encrypted ciphertext")
            continue
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        bad = [m for m in EMAIL_PATTERN.finditer(text) if not _is_allowed_email_domain(m.group(2))]
        findings.extend(f"{rel}: unapproved email domain {m.group(2)!r} in {m.group(1)!r}; {_EMAIL_HINT}" for m in bad)
        for m in SSH_KEY_COMMENT_PATTERN.finditer(text):
            local, _, dom = (comment := m.group(1)).rpartition("@")
            if not (local and _is_allowed_email_domain(dom)):
                findings.append(f"{rel}: SSH key comment {comment!r} {_SSH_HINT}")
        if token_pat is not None and (hit := token_pat.search(text)) is not None:
            findings.append(f"{rel}: contains local workstation identifier {hit.group(0)!r} {_HOST_HINT}")

    if has_git:
        log_cmd = ["git", "-C", str(root), "log", "HEAD", "--format=%h%x09%ae%x09%ce"]
        for line in subprocess.run(log_cmd, check=True, capture_output=True, text=True, timeout=30).stdout.splitlines():  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            if len(parts := line.split("\t")) != 3:
                continue
            pre = f"git commit {parts[0]}"
            for role, email in (("author", parts[1]), ("committer", parts[2])):
                dom = email.partition("@")[2]
                if not dom or not _is_allowed_email_domain(dom):
                    findings.append(f"{pre}: unapproved {role} email {email!r}; use fmind.dev, fmind.ai, or github.com")
                elif token_pat is not None and (hit := token_pat.search(email)) is not None:
                    findings.append(f"{pre}: {role} email contains local workstation identifier {hit.group(0)!r}")
    return sorted(set(findings))


def main() -> int:
    findings = privacy_findings(ROOT)
    for finding in findings:
        sys.stderr.write(f"privacy: {finding}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
