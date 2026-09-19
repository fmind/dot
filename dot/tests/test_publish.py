"""Publication checks use a fake GitHub client and never contact a remote."""

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from dot_tasks.publish import main, publish_release, validate_release_inputs
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


def publication(tmp_path: Path) -> tuple[State, Mock, Path, dict[str, object]]:
    (tmp_path / "dot/dist").mkdir(parents=True)
    (tmp_path / "dot/pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    names = ["package-1.2.3-py3-none-any.whl", "package-1.2.3.tar.gz"]
    for name in names:
        (tmp_path / "dot/dist" / name).write_text(f"fixture {name}")
    notes = tmp_path / "release notes.md"
    notes.write_text("Release notes")
    runner = Mock(spec=Runner)
    assets = [
        {"name": name, "digest": "sha256:" + hashlib.sha256(f"fixture {name}".encode()).hexdigest()} for name in names
    ]
    release: dict[str, object] = {"tagName": "v1.2.3", "isDraft": False, "assets": assets}
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
        (tmp_path / "dot/dist/package-1.2.3-py3-none-any.whl").unlink()
    with pytest.raises(DotError):
        publish_release(state, tmp_path, tag, notes)
    runner.run.assert_not_called()


@pytest.mark.parametrize("create_code", [0, 1])
@pytest.mark.parametrize("digest", ["sha256:" + "0" * 64, None])
def test_same_named_asset_with_other_content_fails_closed(tmp_path: Path, create_code: int, digest: str | None) -> None:
    state, runner, notes, release = publication(tmp_path)
    assets = release["assets"]
    assert isinstance(assets, list)
    assets[0] = {"name": assets[0]["name"], "digest": digest}
    runner.run.side_effect = [CommandResult("", "", create_code), CommandResult(json.dumps(release), "", 0)]
    with pytest.raises(DotError, match="never overwritten"):
        publish_release(state, tmp_path, "v1.2.3", notes)
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == ""
    assert not any("--clobber" in call.args[0] or "upload" in call.args[0] for call in runner.run.call_args_list)


def test_distributions_from_another_version_are_rejected_before_any_remote_call(tmp_path: Path) -> None:
    state, runner, notes, _ = publication(tmp_path)
    wheel = tmp_path / "dot/dist/package-1.2.3-py3-none-any.whl"
    wheel.rename(wheel.with_name("package-1.2.2-py3-none-any.whl"))
    with pytest.raises(DotError, match=r"project version 1\.2\.3"):
        publish_release(state, tmp_path, "v1.2.3", notes)
    runner.run.assert_not_called()


def test_validate_only_checks_inputs_without_a_github_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CD gates attestation on this mode, so it must fail on a wrong tag and never reach gh."""
    _, _, notes, _ = publication(tmp_path)
    assert [path.name for path in validate_release_inputs(tmp_path, "v1.2.3", notes)] == [
        "package-1.2.3-py3-none-any.whl",
        "package-1.2.3.tar.gz",
    ]
    monkeypatch.setattr("dot_tasks.publish.ROOT", tmp_path)
    monkeypatch.setattr(
        "dot_tasks.publish.State", Mock(side_effect=AssertionError("validate-only must not build a client"))
    )
    monkeypatch.setattr("sys.argv", ["publish", "--tag", "v1.2.3", "--notes-file", str(notes), "--validate-only"])
    assert main() == 0
    monkeypatch.setattr("sys.argv", ["publish", "--tag", "v9.9.9", "--notes-file", str(notes), "--validate-only"])
    assert main() == 1
    assert "must match the project version v1.2.3" in capsys.readouterr().err
