"""Exercise clipboard round trips without touching the desktop clipboard."""

import importlib.util
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
            "if mode=='fail': sys.exit(7)\n"
            "reading=Path(sys.argv[0]).name in ('pbpaste','wl-paste') or '-o' in sys.argv\n"
            "if reading:\n"
            "    sys.stdout.buffer.write(b'changed' if mode=='mismatch' else store.read_bytes())\n"
            "else:\n"
            "    store.write_bytes(sys.stdin.buffer.read())\n"
        )
        tool.chmod(0o700)
    return store


@pytest.mark.parametrize(
    ("platform", "names", "display", "wayland"),
    [
        ("darwin", ("pbcopy", "pbpaste"), "", ""),
        ("linux", ("xclip", "wl-copy", "wl-paste"), ":0", "wayland-0"),
        ("linux", ("wl-copy", "wl-paste"), "", "wayland-0"),
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
) -> None:
    store = backend(tmp_path, monkeypatch, names)
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("DISPLAY", display)
    monkeypatch.setenv("WAYLAND_DISPLAY", wayland)
    payload = "Médéric 🦊\n`literal` $(touch should-not-exist)\n\n".encode()
    result = clipboard.copy_text(payload)
    assert store.read_bytes() == payload
    assert "verified" in result
    assert names[0] in result
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
