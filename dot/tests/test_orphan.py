from __future__ import annotations

import hashlib
import io
import json
import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from fmind_dot.errors import DotError
from fmind_dot.orphan import run_orphan
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


class ChezmoiRunner(Runner):
    def __init__(self, entries: object, managed: Sequence[str], *, installed: bool = True) -> None:
        super().__init__()
        self.dump = entries if isinstance(entries, str) else json.dumps({"entryState": entries})
        self.managed = managed
        self.installed = installed

    def which(self, command: str) -> Path | None:
        return Path(f"/tools/{command}") if self.installed else None

    def run(self, args: Sequence[str], **_: object) -> CommandResult:
        if list(args[:3]) == ["chezmoi", "state", "dump"]:
            return CommandResult(self.dump, "", 0)
        assert list(args[:2]) == ["chezmoi", "managed"]
        return CommandResult("\0".join(self.managed), "", 0)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _state(runner: Runner) -> tuple[State, io.StringIO]:
    output = io.StringIO()
    return State(runner=runner, stdout=output), output


def test_orphans_compare_existing_targets_with_the_last_write(tmp_path: Path) -> None:
    kept = tmp_path / "kept.toml"
    kept.write_bytes(b"old\n")
    edited = tmp_path / "edited.timer"
    edited.write_bytes(b"new owner\n")
    link = tmp_path / "skill"
    link.symlink_to("/source/skill")
    empty = tmp_path / "empty"
    empty.mkdir()
    full = tmp_path / "full"
    full.mkdir()
    (full / "config.yaml").write_text("local\n")
    managed = tmp_path / "managed.json"
    managed.write_text("{}")
    entries = {
        str(kept): {"type": "file", "contentsSHA256": _sha(b"old\n")},
        str(edited): {"type": "file", "contentsSHA256": _sha(b"chezmoi\n")},
        str(link): {"type": "symlink", "contentsSHA256": _sha(b"/source/skill")},
        str(empty): {"type": "dir"},
        str(full): {"type": "dir"},
        str(managed): {"type": "file", "contentsSHA256": _sha(b"{}")},
        str(tmp_path / "gone"): {"type": "file", "contentsSHA256": _sha(b"")},
        str(tmp_path / "script.sh"): {"type": "script"},
        str(tmp_path / "removed"): {"type": "remove"},
    }
    state, output = _state(ChezmoiRunner(entries, [str(managed)]))

    orphans = run_orphan(state, as_json=True)

    assert [(Path(item.path).name, item.type, item.status) for item in orphans] == [
        ("edited.timer", "file", "modified"),
        ("empty", "dir", "empty"),
        ("full", "dir", "not-empty"),
        ("kept.toml", "file", "unchanged"),
        ("skill", "symlink", "unchanged"),
    ]
    assert json.loads(output.getvalue())[0] == {"path": str(edited), "type": "file", "status": "modified"}
    # Informational only: nothing is deleted.
    assert all(path.exists() for path in (kept, edited, full))


def test_orphan_reports_a_target_replaced_by_another_type(tmp_path: Path) -> None:
    path = tmp_path / "hooks"
    path.mkdir()
    state, output = _state(ChezmoiRunner({str(path): {"type": "file", "contentsSHA256": _sha(b"x")}}, []))

    assert [item.status for item in run_orphan(state)] == ["replaced"]
    assert "chezmoi state delete --bucket=entryState --key=PATH" in output.getvalue()


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
def test_orphan_marks_unreadable_files_without_failing(tmp_path: Path) -> None:
    secret = tmp_path / "SECRET"
    secret.write_text("value")
    secret.chmod(0)
    try:
        state, _ = _state(ChezmoiRunner({str(secret): {"type": "file", "contentsSHA256": _sha(b"value")}}, []))
        assert [item.status for item in run_orphan(state)] == ["unreadable"]
    finally:
        secret.chmod(0o600)


def test_orphan_without_leftovers_says_so() -> None:
    state, output = _state(ChezmoiRunner({}, []))

    assert run_orphan(state) == []
    assert output.getvalue() == "✓ No orphaned chezmoi targets.\n"


@pytest.mark.parametrize("dump", ["not json", json.dumps({"configState": {}})], ids=["invalid", "no-bucket"])
def test_orphan_rejects_unreadable_state(dump: str) -> None:
    with pytest.raises(DotError, match="chezmoi state dump"):
        run_orphan(_state(ChezmoiRunner(dump, []))[0])


def test_orphan_requires_chezmoi() -> None:
    with pytest.raises(DotError, match="chezmoi"):
        run_orphan(_state(ChezmoiRunner({}, [], installed=False))[0])


def test_orphan_skips_a_target_removed_while_scanning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "leftover"
    path.write_text("x")
    state, _ = _state(ChezmoiRunner({str(path): {"type": "file", "contentsSHA256": _sha(b"x")}}, []))

    def vanished(_: Path) -> str:
        raise FileNotFoundError(path)

    monkeypatch.setattr("fmind_dot.orphan._sha256", vanished)

    assert run_orphan(state) == []
