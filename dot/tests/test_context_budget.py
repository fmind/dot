"""Observable context reports with isolated global and project inputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer._click.utils import strip_ansi
from typer.testing import CliRunner

from fmind_dot.cli import app
from fmind_dot.context_budget import MAX_INPUT_BYTES, context_report
from fmind_dot.errors import DotError

runner = CliRunner()


def skill(root: Path, name: str, *, description: str = "Run a fixture.") -> Path:
    path = root / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n# Private instructions\n")
    return path


def test_cli_reports_scopes_and_excludes_on_demand_content(tmp_path: Path) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    skill(global_root, "global-fixture")
    local = skill(project / ".agents", "local-fixture")
    (local.parent / "references").mkdir()
    (local.parent / "references/large.md").write_text("private reference " * 10_000)
    (global_root / "AGENTS.md").write_text("G" * 16)
    (project / "AGENTS.md").write_text("P" * 8)
    result = runner.invoke(
        app, ["agent", "context", "--project", str(project), "--global-root", str(global_root), "--json", "--check"]
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["schema"] == "dot.agent.context/v4"
    assert report["totals"]["global"]["agents_estimated_tokens"] == 4
    assert report["totals"]["local"]["agents_estimated_tokens"] == 2
    assert report["totals"]["combined"]["skills"] == 2
    assert report["passed"] is True
    assert "Private instructions" not in result.stdout
    assert "private reference" not in result.stdout
    before = report["totals"]["combined"]
    local.write_text(local.read_text() + "body only " * 200)
    after = context_report(project, global_root=global_root)["totals"]["combined"]
    assert after["skill_index_estimated_tokens"] == before["skill_index_estimated_tokens"]
    assert after["on_demand_skill_file_estimated_tokens"] > before["on_demand_skill_file_estimated_tokens"]


def test_source_mode_reads_authored_persona_and_both_catalogs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    skill(source, "global-fixture")
    skill(source / ".agents", "local-fixture")
    (source / "dot_agents").mkdir()
    (source / "dot_agents/AGENTS.md").write_text("global source\n")
    (source / "AGENTS.md").write_text("local source\n")
    report = context_report(source, source=source)
    assert report["totals"]["combined"]["skills"] == 2
    assert report["totals"]["combined"]["agents_files"] == 2
    assert report["roots"]["global"]["agents"].endswith("dot_agents/AGENTS.md")


def test_combined_deduplicates_physical_files_and_exposes_name_collisions(tmp_path: Path) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    path = skill(global_root, "shared")
    local = project / ".agents/skills"
    local.mkdir(parents=True)
    (local / "shared").symlink_to(path.parent, target_is_directory=True)
    report = context_report(project, global_root=global_root)
    assert report["totals"]["global"]["skills"] == report["totals"]["local"]["skills"] == 1
    assert report["totals"]["combined"]["skills"] == 1
    assert report["collisions"] == []
    (local / "shared").unlink()
    skill(project / ".agents", "shared")
    report = context_report(project, global_root=global_root)
    assert report["totals"]["combined"]["skills"] == 2
    assert report["collisions"] == ["shared"]


def test_context_ignores_reserved_skill_directories(tmp_path: Path) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    skill(global_root, "global-fixture")
    skill(project / ".agents", "local-fixture")
    synced = global_root / "skills/synced/remote-bucket/remote-skill"
    synced.mkdir(parents=True)
    (synced / "SKILL.md").write_text("---\nname: remote-skill\ndescription: Remote fixture.\n---\n")
    report = context_report(project, global_root=global_root)
    assert report["totals"]["global"]["skills"] == 1


@pytest.mark.parametrize("scope", ["global", "local"])
@pytest.mark.parametrize(("tokens", "passed"), [(4_999, True), (5_000, False), (5_001, False)])
def test_check_includes_instructions_and_enforces_each_strict_limit(
    tmp_path: Path, scope: str, tokens: int, passed: bool
) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    skill(global_root, "global-fixture")
    skill(project / ".agents", "local-fixture")
    report = context_report(project, global_root=global_root)
    index_size = report["totals"][scope]["skill_index_characters"]
    instructions = (global_root if scope == "global" else project) / "AGENTS.md"
    instructions.write_text("x" * (tokens * 4 - index_size))
    arguments = ["agent", "context", "--project", str(project), "--global-root", str(global_root)]
    plain = runner.invoke(app, arguments)
    assert plain.exit_code == 0
    assert ("OVER BUDGET" not in plain.stdout) == passed
    checked = runner.invoke(app, [*arguments, "--check", "--json"])
    assert checked.exit_code == (0 if passed else 1)
    report = json.loads(checked.stdout)
    assert report["passed"] == passed
    assert report["budgets"][scope] == {
        "limit_exclusive": 5_000,
        "estimated_tokens": tokens,
        "remaining": 4_999 - tokens,
        "passed": passed,
    }
    other_scope = "local" if scope == "global" else "global"
    assert report["budgets"][other_scope]["passed"] is True


def test_combined_total_can_exceed_limit_when_each_scope_fits(tmp_path: Path) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    skill(global_root, "global-fixture")
    skill(project / ".agents", "local-fixture")
    (global_root / "AGENTS.md").write_text("g" * 12_000)
    (project / "AGENTS.md").write_text("p" * 12_000)
    result = runner.invoke(
        app, ["agent", "context", "--project", str(project), "--global-root", str(global_root), "--json", "--check"]
    )
    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["totals"]["combined"]["startup_estimated_tokens"] > 5_000
    assert report["passed"] is True
    assert set(report["budgets"]) == {"global", "local"}


@pytest.mark.parametrize(
    "content",
    [
        "no frontmatter",
        "---\nname: broken\n",
        "---\nname: [private: !!bad\n---\n",
        "---\nname: wrong\ndescription: test\n---\n",
        "---\nname: broken\ndescription: 42\n---\n",
        "---\n- private\n---\n",
    ],
)
def test_bad_metadata_fails_without_printing_instruction_content(tmp_path: Path, content: str) -> None:
    path = skill(tmp_path, "broken")
    path.write_text(content)
    with pytest.raises(DotError) as caught:
        context_report(tmp_path, global_root=tmp_path)
    message = str(caught.value).replace(str(path), "")
    assert "private" not in message


def test_broken_symlink_and_oversized_input_fail_instead_of_undercounting(tmp_path: Path) -> None:
    path = skill(tmp_path, "fixture")
    link = path.parent.parent / "retired"
    link.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(DotError, match="broken skill link"):
        context_report(tmp_path, global_root=tmp_path)
    link.unlink()
    path.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
    with pytest.raises(DotError, match="exceeds 1 MiB"):
        context_report(tmp_path, global_root=tmp_path)
    path.write_bytes(b"\xff")
    with pytest.raises(DotError, match="UTF-8"):
        context_report(tmp_path, global_root=tmp_path)


def test_empty_roots_and_default_home_are_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["agent", "context", "--json"])
    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["totals"]["combined"]["startup_estimated_tokens"] == 0
    assert report["roots"]["global"]["skills"] == str(tmp_path / ".agents/skills")


def test_invalid_roots_and_conflicting_source_options(tmp_path: Path) -> None:
    with pytest.raises(DotError, match="project directory"):
        context_report(tmp_path / "missing")
    with pytest.raises(DotError, match="invalid dot source"):
        context_report(tmp_path, source=tmp_path)
    result = runner.invoke(app, ["agent", "context", "--source", str(tmp_path), "--global-root", str(tmp_path)])
    assert result.exit_code == 2
    assert "choose --source or --global-root" in strip_ansi(result.output)


def test_nonregular_instruction_input_fails_without_opening_it(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").mkdir()
    with pytest.raises(DotError, match="not a regular file"):
        context_report(tmp_path, global_root=tmp_path / "global")


@pytest.mark.parametrize("tokens", [3_499, 3_500, 3_501, 4_500])
def test_combined_discovery_is_informational_when_each_scope_fits(tmp_path: Path, tokens: int) -> None:
    global_root, project = tmp_path / "global", tmp_path / "project"
    path = skill(global_root, "fixture", description="x")
    skill(project / ".agents", "local-fixture")
    before = context_report(project, global_root=global_root)
    additional = tokens * 4 - before["totals"]["combined"]["skill_index_characters"]
    path.write_text(path.read_text().replace("description: x", "description: " + "x" * (additional + 1)))
    result = runner.invoke(
        app, ["agent", "context", "--project", str(project), "--global-root", str(global_root), "--check", "--json"]
    )
    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["budgets"]["global"]["passed"]
    assert report["budgets"]["local"]["passed"]
    assert report["totals"]["combined"]["skill_index_estimated_tokens"] == tokens
    assert set(report["budgets"]) == {"global", "local"}
    assert report["passed"] is True


def test_nested_skill_counts_through_link_but_guide_stays_on_demand(tmp_path: Path) -> None:
    package = skill(tmp_path / "source", "parent")
    nested = skill(package.parent, "child")
    guide = package.parent / "references/ruff.md"
    guide.parent.mkdir()
    guide.write_text("---\nname: ruff\ndescription: Format Python.\n---\n# Ruff\n")
    installed = tmp_path / "global/skills"
    installed.mkdir(parents=True)
    (installed / "parent").symlink_to(package.parent, target_is_directory=True)
    report = context_report(tmp_path, global_root=installed.parent)
    assert report["totals"]["global"]["skills"] == 2
    assert {entry["name"] for entry in report["entries"]} == {"parent", "child"}
    nested.unlink()
    after = context_report(tmp_path, global_root=installed.parent)
    assert after["totals"]["global"]["skills"] == 1
    assert after["totals"]["global"]["skill_index_characters"] < report["totals"]["global"]["skill_index_characters"]


def test_recursive_directory_link_fails_with_recovery_guidance(tmp_path: Path) -> None:
    path = skill(tmp_path, "parent")
    (path.parent / "cycle").symlink_to(path.parent, target_is_directory=True)
    with pytest.raises(DotError, match=r"cyclic skill directory.*remove the recursive link"):
        context_report(tmp_path, global_root=tmp_path)
