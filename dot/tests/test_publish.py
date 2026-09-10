"""Publication checks use a fake GitHub client and never contact a remote."""

import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from dot_tasks.publish import publish_release
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


def publication(tmp_path: Path) -> tuple[State, Mock, Path, dict[str, object]]:
    (tmp_path / "dot/dist").mkdir(parents=True)
    (tmp_path / "dot/pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    names = ["package-1.2.3.whl", "package-1.2.3.tar.gz"]
    for name in names:
        (tmp_path / "dot/dist" / name).write_text("fixture")
    notes = tmp_path / "release notes.md"
    notes.write_text("Release notes")
    runner = Mock(spec=Runner)
    release: dict[str, object] = {"tagName": "v1.2.3", "isDraft": False, "assets": [{"name": name} for name in names]}
    return State(runner=runner, stdout=io.StringIO()), runner, notes, release


@pytest.mark.parametrize("create_code", [0, 1])
def test_publication_and_retry_require_public_assets(tmp_path: Path, create_code: int) -> None:
    state, runner, notes, release = publication(tmp_path)
    runner.run.side_effect = [CommandResult("", "", create_code), CommandResult(json.dumps(release), "", 0)]
    publish_release(state, tmp_path, "v1.2.3", notes)
    assert isinstance(state.stdout, io.StringIO)
    assert "v1.2.3" in state.stdout.getvalue()
    create = runner.run.call_args_list[0].args[0]
    assert create[:4] == ["gh", "release", "create", "v1.2.3"]
    assert "--verify-tag" in create
    assert "--clobber" not in create
    assert create[-1] == str(notes)


@pytest.mark.parametrize("change", [{"isDraft": True}, {"tagName": "v0.0.0"}, {"assets": []}, {"assets": None}])
def test_incomplete_existing_release_fails(tmp_path: Path, change: dict[str, object]) -> None:
    state, runner, notes, release = publication(tmp_path)
    release.update(change)
    runner.run.side_effect = [CommandResult("", "already exists", 1), CommandResult(json.dumps(release), "", 0)]
    with pytest.raises(DotError):
        publish_release(state, tmp_path, "v1.2.3", notes)
    assert runner.run.call_count == 2


def test_lookup_failure_never_becomes_success(tmp_path: Path) -> None:
    state, runner, notes, _ = publication(tmp_path)
    runner.run.side_effect = [CommandResult("", "network failure", 1), DotError("lookup failed")]
    with pytest.raises(DotError, match="lookup failed"):
        publish_release(state, tmp_path, "v1.2.3", notes)
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == ""


@pytest.mark.parametrize("problem", ["tag", "notes", "wheel"])
def test_invalid_inputs_do_not_publish(tmp_path: Path, problem: str) -> None:
    state, runner, notes, _ = publication(tmp_path)
    tag = "v0.0.0" if problem == "tag" else "v1.2.3"
    if problem == "notes":
        notes.unlink()
    if problem == "wheel":
        (tmp_path / "dot/dist/package-1.2.3.whl").unlink()
    with pytest.raises(DotError):
        publish_release(state, tmp_path, tag, notes)
    runner.run.assert_not_called()
