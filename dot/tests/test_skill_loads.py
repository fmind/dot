"""Count observed skill loads from synthetic agy, Claude, and Pi transcripts."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "skills/skillify/scripts/skill_loads.py"
CATALOG = ("alpha", "beta", *(f"bulk-{index}" for index in range(8)))


def _jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _skill(home: Path, name: str) -> str:
    return str(home / ".agents/skills" / name / "SKILL.md")


def _run(home: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *arguments],
        env={**os.environ, "HOME": str(home)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _home(tmp_path: Path) -> Path:
    for name in CATALOG:
        (tmp_path / ".agents/skills" / name).mkdir(parents=True)
        (tmp_path / ".agents/skills" / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    agy = tmp_path / ".gemini/antigravity-cli/brain"
    # A task that read one skill twice, and quoted another without reading it.
    _jsonl(
        agy / "task/.system_generated/logs/transcript_full.jsonl",
        [
            {"type": "USER_INPUT", "content": f"private prompt quoting {_skill(tmp_path, 'beta')}"},
            {"tool_calls": [{"name": "read_file", "args": {"AbsolutePath": _skill(tmp_path, "alpha")}}]},
            {"tool_calls": [{"name": "view_file", "args": {"AbsolutePath": _skill(tmp_path, "alpha")}}]},
            {"tool_calls": [{"name": "run_command", "args": {"CommandLine": f"cat {_skill(tmp_path, 'beta')}"}}]},
        ],
    )
    # A catalog review reads everything: it is no evidence that a task needed any of them.
    _jsonl(
        agy / "audit/.system_generated/logs/transcript.jsonl",
        [{"tool_calls": [{"name": "read_file", "args": {"AbsolutePath": _skill(tmp_path, name)}}]} for name in CATALOG],
    )
    claude = tmp_path / ".claude/projects/-work-project"
    tools = [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "beta"}},
        {"type": "tool_use", "name": "Read", "input": {"file_path": _skill(tmp_path, "alpha")}},
        {"type": "tool_use", "name": "Skill", "input": {"skill": "not-in-catalog"}},
    ]
    _jsonl(claude / "session.jsonl", [{"type": "assistant", "message": {"content": tools}}, {"type": "user"}])
    _jsonl(claude / "session/subagents/agent-1.jsonl", [{"type": "assistant", "message": {"content": tools}}])
    (claude / "broken.jsonl").write_text('{"message": {"content": [{"type": "tool_use"\n', encoding="utf-8")
    call = {"type": "toolCall", "id": "c1", "name": "read", "arguments": {"path": "skills/beta/SKILL.md"}}
    _jsonl(
        tmp_path / ".pi/agent/sessions/--work-project--/2026-11-09T20-57-49-274Z_pi-id.jsonl",
        [{"type": "message", "message": {"role": "assistant", "content": [call]}}],
    )
    (tmp_path / ".pi/agent/sessions/--work-project--/dangling.jsonl").symlink_to(tmp_path / "missing.jsonl")
    return tmp_path


def test_counts_tool_loads_per_harness_and_excludes_audits(tmp_path: Path) -> None:
    result = _run(_home(tmp_path), "--json")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["schema"] == "skillify.skill-loads/v1"
    # The subagent transcript is not a session; the malformed one is, and loads nothing.
    assert report["sessions"] == {"agy": 2, "claude": 2, "pi": 1}
    assert report["audit_sessions_excluded"] == {"agy": 1, "claude": 0, "pi": 0}
    assert report["skills"][:2] == [
        {"skill": "alpha", "agy": 1, "claude": 1, "pi": 0, "total": 2},
        {"skill": "beta", "agy": 0, "claude": 1, "pi": 1, "total": 2},
    ]
    assert all(row["total"] == 0 for row in report["skills"][2:])


def test_text_report_names_unloaded_skills_and_no_transcript_content(tmp_path: Path) -> None:
    result = _run(_home(tmp_path))

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "Skill loads over 30 days · sessions: agy=2 claude=2 pi=1 · audits excluded: agy=1 claude=0 pi=0"
    assert lines[1:3] == ["alpha  agy=1 claude=1 pi=0", "beta   agy=0 claude=1 pi=1"]
    assert lines[3] == "No observed load (8): " + " ".join(f"bulk-{index}" for index in range(8))
    assert "private prompt" not in result.stdout


def test_window_excludes_older_sessions_and_bad_arguments_exit_two(tmp_path: Path) -> None:
    home = _home(tmp_path)
    for path in home.rglob("*.jsonl"):
        if path.exists():
            os.utime(path, (0, 0))

    aged = json.loads(_run(home, "--json", "--days", "7").stdout)

    assert aged["sessions"] == {"agy": 0, "claude": 0, "pi": 0}
    assert _run(home, "--days", "0").returncode == 2
    missing = _run(home, "--skills", str(tmp_path / "missing"))
    assert missing.returncode == 2
    assert "no skills found" in missing.stderr
