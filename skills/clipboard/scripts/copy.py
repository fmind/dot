"""Copy UTF-8 stdin to the local system clipboard and verify its bytes."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import IO

LIMIT = 1024 * 1024  # Clipboard deliverables are short; larger content belongs in a file.
TIMEOUT = 5


def commands() -> tuple[list[str], list[str]]:
    """Choose the native backend without probing or reading clipboard contents."""
    if sys.platform == "darwin":
        names = ("pbcopy", "pbpaste")
        paths = [shutil.which(name) for name in names]
        if all(paths):
            return [str(paths[0])], [str(paths[1])]
        raise RuntimeError("macOS requires pbcopy and pbpaste in PATH")
    if sys.platform.startswith("linux"):
        xclip = shutil.which("xclip")
        copy, paste = shutil.which("wl-copy"), shutil.which("wl-paste")
        x11 = ([xclip, "-selection", "clipboard"], [xclip, "-selection", "clipboard", "-o"]) if xclip else None
        wayland = ([copy, "--type", "text/plain;charset=utf-8"], [paste, "--no-newline"]) if copy and paste else None
        # Crostini's Sommelier syncs the X11 clipboard with ChromeOS; native Wayland
        # desktops would otherwise route through XWayland, which some compositors break.
        prefer_x11 = bool(os.environ.get("SOMMELIER_VERSION")) or not os.environ.get("WAYLAND_DISPLAY")
        order = ((os.environ.get("DISPLAY"), x11), (os.environ.get("WAYLAND_DISPLAY"), wayland))
        for session, backend in order if prefer_x11 else reversed(order):
            if session and backend:
                return backend
        raise RuntimeError("Linux requires DISPLAY with xclip, or WAYLAND_DISPLAY with wl-copy and wl-paste")
    raise RuntimeError("supported platforms: macOS and ChromeOS/Linux")


def environment() -> dict[str, str]:
    """pbcopy and pbpaste transcode through the locale; pin UTF-8 so read-back matches."""
    env = dict(os.environ)
    if sys.platform == "darwin":
        env["LC_CTYPE"] = "UTF-8"
    return env


def diagnostics(errors: IO[bytes]) -> str:
    """Return a short tail of the native tool's stderr; it never contains the payload."""
    errors.seek(0)
    text = " ".join(errors.read()[-300:].decode("utf-8", "replace").split())
    return f": {text}" if text else ""


def copy_text(payload: bytes, *, keep_final_newline: bool = False) -> str:
    if not keep_final_newline and payload.endswith(b"\n"):
        payload = payload[:-1]  # A heredoc always appends one newline.
    if not payload:
        raise ValueError("nothing to copy; select a deliverable before invoking the helper")
    if len(payload) > LIMIT:
        raise ValueError(f"{len(payload)} bytes exceeds the {LIMIT}-byte limit; write the content to a file instead")
    payload.decode("utf-8")
    if b"\0" in payload:
        raise ValueError("clipboard text must not contain NUL bytes")
    copy, paste = commands()
    env = environment()
    # Clipboard owners fork and keep serving the selection. Pipes inherited by
    # those children would keep subprocess.run(capture_output=True) waiting.
    with tempfile.TemporaryFile() as errors:
        written = subprocess.run(  # noqa: S603 - fixed native executable; payload is stdin
            copy, input=payload, stdout=subprocess.DEVNULL, stderr=errors, env=env, timeout=TIMEOUT, check=False
        )
        if written.returncode:
            raise RuntimeError(f"{Path(copy[0]).name} failed (exit {written.returncode}){diagnostics(errors)}")
        read = subprocess.run(  # noqa: S603 - fixed native executable and arguments
            paste,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=errors,
            env=env,
            timeout=TIMEOUT,
            check=False,
        )
        if read.returncode:
            raise RuntimeError(
                f"{Path(paste[0]).name} failed (exit {read.returncode}); verification unavailable{diagnostics(errors)}"
            )
    if read.stdout != payload:
        raise RuntimeError("clipboard read-back differs from the selected text; clipboard state is uncertain")
    return f"Copied {len(payload)} UTF-8 bytes via {Path(copy[0]).name}; clipboard verified."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-final-newline", action="store_true", help="keep one trailing newline instead of stripping it"
    )
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(copy_text(sys.stdin.buffer.read(), keep_final_newline=args.keep_final_newline) + "\n")
    except (ValueError, RuntimeError, OSError) as error:
        sys.stderr.write(f"Clipboard error: {error}\n")
        return 1
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "Clipboard error: native command timed out; check the local display session. Clipboard state is uncertain.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
