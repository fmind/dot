"""Copy UTF-8 stdin to the local system clipboard and verify its bytes."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
        if os.environ.get("DISPLAY") and xclip:
            return [xclip, "-selection", "clipboard"], [xclip, "-selection", "clipboard", "-o"]
        copy, paste = shutil.which("wl-copy"), shutil.which("wl-paste")
        if os.environ.get("WAYLAND_DISPLAY") and copy and paste:
            return [copy, "--type", "text/plain;charset=utf-8"], [paste, "--no-newline"]
        raise RuntimeError("Linux requires DISPLAY with xclip, or WAYLAND_DISPLAY with wl-copy and wl-paste")
    raise RuntimeError("supported platforms: macOS and ChromeOS/Linux")


def copy_text(payload: bytes) -> str:
    if not payload:
        raise ValueError("nothing to copy; select a deliverable before invoking the helper")
    payload.decode("utf-8")
    if b"\0" in payload:
        raise ValueError("clipboard text must not contain NUL bytes")
    copy, paste = commands()
    # Clipboard owners fork and keep serving the selection. Pipes inherited by
    # those children would keep subprocess.run(capture_output=True) waiting.
    with tempfile.TemporaryFile() as errors:
        written = subprocess.run(  # noqa: S603 - fixed native executable; payload is stdin
            copy, input=payload, stdout=subprocess.DEVNULL, stderr=errors, timeout=5, check=False
        )
        if written.returncode:
            raise RuntimeError(f"{Path(copy[0]).name} failed (exit {written.returncode}); check the display session")
        read = subprocess.run(  # noqa: S603 - fixed native executable and arguments
            paste, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors, timeout=5, check=False
        )
    if read.returncode:
        raise RuntimeError(f"{Path(paste[0]).name} failed (exit {read.returncode}); clipboard verification unavailable")
    if read.stdout != payload:
        raise RuntimeError("clipboard read-back differs from the selected text; clipboard state is uncertain")
    return f"Copied {len(payload)} UTF-8 bytes via {Path(copy[0]).name}; clipboard verified."


def main() -> int:
    try:
        sys.stdout.write(copy_text(sys.stdin.buffer.read()) + "\n")
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
