"""Exercise clipboard round trips without touching the desktop clipboard."""

import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/clipboard/scripts/copy.py"


@pytest.fixture
def clipboard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("clipboard_copy", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, names: tuple[str, ...], *, mode: str = "ok") -> Path:
    store = tmp_path / "clipboard"
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("FAKE_CLIPBOARD", str(store))
    monkeypatch.setenv("FAKE_MODE", mode)
    for name in names:
        tool = tmp_path / name
        tool.write_text(
            f"#!{sys.executable}\n"
            "import os,sys\nfrom pathlib import Path\n"
            "store=Path(os.environ['FAKE_CLIPBOARD'])\n"
            "mode=os.environ['FAKE_MODE']\n"
            "if mode=='fail': sys.stderr.write(\"Error: Can't open display\\n\"); sys.exit(7)\n"
            "if mode=='hang': import time; time.sleep(30)\n"
            "reading=Path(sys.argv[0]).name in ('pbpaste','wl-paste') or '-o' in sys.argv\n"
            "if reading:\n"
            "    sys.stdout.buffer.write(b'changed' if mode=='mismatch' else store.read_bytes())\n"
            "else:\n"
            "    store.write_bytes(sys.stdin.buffer.read())\n"
        )
        tool.chmod(0o700)
    return store


@pytest.mark.parametrize(
    ("platform", "names", "display", "wayland", "sommelier", "expected"),
    [
        ("darwin", ("pbcopy", "pbpaste"), "", "", "", "pbcopy"),
        # Both displays: ChromeOS Sommelier prefers X11; other desktops prefer native Wayland.
        ("linux", ("xclip", "wl-copy", "wl-paste"), ":0", "wayland-0", "1", "xclip"),
        ("linux", ("xclip", "wl-copy", "wl-paste"), ":0", "wayland-0", "", "wl-copy"),
        ("linux", ("wl-copy", "wl-paste"), "", "wayland-0", "", "wl-copy"),
    ],
)
def test_native_round_trip_preserves_literal_utf8(
    clipboard: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    names: tuple[str, ...],
    display: str,
    wayland: str,
    sommelier: str,
    expected: str,
) -> None:
    store = backend(tmp_path, monkeypatch, names)
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("DISPLAY", display)
    monkeypatch.setenv("WAYLAND_DISPLAY", wayland)
    if sommelier:
        monkeypatch.setenv("SOMMELIER_VERSION", sommelier)
    else:
        monkeypatch.delenv("SOMMELIER_VERSION", raising=False)
    payload = "Médéric 🦊\n`literal` $(touch should-not-exist)\n\n".encode()
    result = clipboard.copy_text(payload)
    assert store.read_bytes() == payload[:-1]
    assert "verified" in result
    assert expected in result
    assert "Médéric" not in result
    assert not (tmp_path / "should-not-exist").exists()


@pytest.mark.parametrize("payload", [b"", b"\xff", b"a\0b"])
def test_invalid_payload_preserves_existing_clipboard(
    clipboard: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    store = backend(tmp_path, monkeypatch, ("pbcopy", "pbpaste"))
    monkeypatch.setattr(sys, "platform", "darwin")
    store.write_bytes(b"preserve")
    with pytest.raises(ValueError, match=r"nothing to copy|utf-8|NUL"):
        clipboard.copy_text(payload)
    assert store.read_bytes() == b"preserve"


@pytest.mark.parametrize(("mode", "message"), [("fail", "exit 7"), ("mismatch", "differs")])
def test_failed_copy_never_reports_success(
    clipboard: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, message: str
) -> None:
    backend(tmp_path, monkeypatch, ("pbcopy", "pbpaste"), mode=mode)
    monkeypatch.setattr(sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match=message):
        clipboard.copy_text(b"private content")


def test_headless_session_preserves_existing_clipboard(
    clipboard: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = backend(tmp_path, monkeypatch, ("xclip", "wl-copy", "wl-paste"))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    store.write_bytes(b"preserve")
    with pytest.raises(RuntimeError, match="DISPLAY"):
        clipboard.copy_text(b"new")
    assert store.read_bytes() == b"preserve"


@pytest.mark.parametrize(("keep", "expected"), [(False, b"command"), (True, b"command\n")])
def test_one_final_newline_is_stripped_unless_kept(
    clipboard: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keep: bool, expected: bytes
) -> None:
    store = backend(tmp_path, monkeypatch, ("pbcopy", "pbpaste"))
    monkeypatch.setattr(sys, "platform", "darwin")
    clipboard.copy_text(b"command\n", keep_final_newline=keep)
    assert store.read_bytes() == expected
    assert clipboard.environment()["LC_CTYPE"] == "UTF-8"


def test_lone_newline_and_oversized_payloads_are_rejected(clipboard: ModuleType) -> None:
    with pytest.raises(ValueError, match="nothing to copy"):
        clipboard.copy_text(b"\n")
    with pytest.raises(ValueError, match="limit"):
        clipboard.copy_text(b"x" * (clipboard.LIMIT + 1))


@pytest.mark.parametrize(
    ("names", "sommelier", "expected"),
    [
        (("xclip", "wl-copy", "wl-paste"), "0.20", "xclip"),
        (("xclip", "wl-copy", "wl-paste"), "", "wl-copy"),
        (("wl-copy", "wl-paste"), "0.20", "wl-copy"),
    ],
)
def test_linux_backend_prefers_x11_only_on_crostini(
    clipboard: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...],
    sommelier: str,
    expected: str,
) -> None:
    backend(tmp_path, monkeypatch, names)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("SOMMELIER_VERSION", sommelier)
    assert expected in clipboard.copy_text(b"text")


def test_backend_failure_reports_native_diagnostics(
    clipboard: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend(tmp_path, monkeypatch, ("pbcopy", "pbpaste"), mode="fail")
    monkeypatch.setattr(sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match="Can't open display"):
        clipboard.copy_text(b"text")


def test_main_reports_timeout_without_claiming_success(
    clipboard: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backend(tmp_path, monkeypatch, ("pbcopy", "pbpaste"), mode="hang")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(clipboard, "TIMEOUT", 0.5)
    monkeypatch.setattr(sys, "stdin", type("Stdin", (), {"buffer": io.BytesIO(b"text")})())
    assert clipboard.main([]) == 1
    captured = capsys.readouterr()
    assert "timed out" in captured.err
    assert "verified" not in captured.out
