"""Inject one validated secret into a child process environment without argv exposure."""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Never

from fmind_dot.errors import suppress_broken_pipe_stdout

_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_MAX_SECRET_BYTES = 65_536
_SECRETS_REL = Path(".config/dot/secrets")


def _fail(message: str, code: int = 1) -> Never:
    sys.stderr.write(f"with-secret: error: {message}\n")
    raise SystemExit(code)


def _write_stdout(text: str) -> Never:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        suppress_broken_pipe_stdout()
    raise SystemExit(0)


def _read_secret_file(name: str) -> str:
    secrets_dir = Path.home() / _SECRETS_REL
    try:
        dir_fd = os.open(secrets_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        _fail(f"{name}: cannot read personal secret; configure ~/.config/dot/secrets/{name}")
    except OSError:
        _fail(f"{name}: personal secret directory must be an owner-only directory (chmod 700)")
    try:
        dir_st = os.fstat(dir_fd)
        if dir_st.st_uid != os.getuid() or (stat.S_IMODE(dir_st.st_mode) & 0o077) != 0:
            _fail(f"{name}: personal secret directory must be an owner-only directory (chmod 700)")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
        except FileNotFoundError:
            _fail(f"{name}: cannot read personal secret; configure ~/.config/dot/secrets/{name}")
        except OSError:
            _fail(f"{name}: personal secret must be an owner-only regular file (chmod 600)")
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or (stat.S_IMODE(st.st_mode) & 0o077) != 0:
                _fail(f"{name}: personal secret must be an owner-only regular file (chmod 600)")
            chunks: list[bytes] = []
            remaining = _MAX_SECRET_BYTES + 1
            while remaining > 0 and (chunk := os.read(fd, remaining)):
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(dir_fd)
    if len(raw) > _MAX_SECRET_BYTES:
        _fail(f"{name}: personal secret exceeds 64 KiB")
    if b"\x00" in raw:
        _fail(f"{name}: personal secret contains a NUL byte")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail(f"{name}: personal secret is not valid UTF-8")
    val = text.rstrip("\r\n")
    if not val or "\r" in val or "\n" in val:
        _fail(f"{name}: personal secret is empty or contains a line break")
    return val


def main(
    argv: Sequence[str] | None = None,
    *,
    exec_fn: Callable[[str, list[str], dict[str, str]], object] = os.execve,
) -> None:
    """Run COMMAND with NAME injected into its child environment only."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        _write_stdout(
            "usage: with-secret [-h] [-V] NAME [--] COMMAND [ARGS...]\n\n"
            "Run COMMAND with NAME injected into its child environment only.\n\n"
            "options:\n"
            "  -h, --help     show this help message and exit\n"
            "  -V, --version  show program's version number and exit\n\n"
            "Exit codes: 0 help/version or child exit 0; 1 missing or unsafe secret, or command not found/exec error; "
            "2 usage error (missing args, invalid NAME, or retired UV_PUBLISH_TOKEN); else child exit code.\n\n"
            "Examples: with-secret OPENROUTER_MANAGEMENT_KEY -- <command> · with-secret MY_KEY env\n"
        )
    if args and args[0] in {"-V", "--version"}:
        from fmind_dot import __version__

        _write_stdout(f"with-secret version {__version__}\n")
    if len(args) < 2:
        _fail("usage: with-secret [-h] [-V] NAME [--] COMMAND [ARGS...]", 2)
    name = args[0]
    if not _NAME_RE.fullmatch(name):
        _fail("NAME: expected an uppercase environment variable name", 2)
    # PyPI packages publish through Trusted Publishing in CI, not a personal token.
    if name == "UV_PUBLISH_TOKEN":
        _fail("NAME: PyPI publishing uses Trusted Publishing, not a personal token", 2)
    cmd = args[2:] if args[1] == "--" else args[1:]
    if not cmd:
        _fail("missing COMMAND after --", 2)
    executable = shutil.which(cmd[0])
    if executable is None:
        _fail(f"required tools are missing: {cmd[0]}")
    if name in os.environ:
        val = os.environ[name]
        if not val or "\r" in val or "\n" in val:
            _fail(f"{name}: credential is empty or contains a line break; no personal fallback was used")
    else:
        val = _read_secret_file(name)
    try:
        exec_fn(executable, cmd, {**os.environ, name: val})
    except OSError as error:
        _fail(f"failed to execute {cmd[0]}: {error.strerror or error}")
