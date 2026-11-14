"""Count observed skill loads from synthetic agy, Claude, and Pi transcripts."""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
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


def test_claude_subagent_and_slash_skill_loads_roll_into_parent_session(tmp_path: Path) -> None:
    home = _home(tmp_path)
    claude = home / ".claude/projects/-work-project"
    _jsonl(
        claude / "session/subagents/agent-2.jsonl",
        [
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "/bulk-0"}}]},
            }
        ],
    )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row for row in report["skills"]}

    assert report["sessions"] == {"agy": 2, "claude": 2, "pi": 1}
    assert by_skill["bulk-0"] == {"skill": "bulk-0", "agy": 0, "claude": 1, "pi": 0, "total": 1}


def test_agy_subagent_loads_roll_into_root_conversation(tmp_path: Path) -> None:
    home = _home(tmp_path)
    app_dir = home / ".gemini/antigravity-cli"
    _jsonl(
        app_dir / "brain/child/.system_generated/logs/transcript.jsonl",
        [{"tool_calls": [{"name": "read_file", "args": {"Path": _skill(home, "beta")}}]}],
    )
    with closing(sqlite3.connect(app_dir / "conversation_summaries.db")) as conn, conn:
        conn.execute("CREATE TABLE conversation_summaries (conversation_id TEXT, parent_conversation_id TEXT)")
        conn.executemany(
            "INSERT INTO conversation_summaries VALUES (?, ?)",
            [("task", ""), ("child", "task"), ("cycle-a", "cycle-b"), ("cycle-b", "cycle-a")],
        )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row for row in report["skills"]}

    assert report["sessions"] == {"agy": 2, "claude": 2, "pi": 1}
    assert by_skill["alpha"] == {"skill": "alpha", "agy": 1, "claude": 1, "pi": 0, "total": 2}
    assert by_skill["beta"] == {"skill": "beta", "agy": 1, "claude": 1, "pi": 1, "total": 3}


def test_direct_reference_guide_reads_count_as_skill_loads_without_double_counting(tmp_path: Path) -> None:
    home = _home(tmp_path)
    alpha_guide = str(home / ".agents/skills/alpha/references/guide.md")
    bulk_guide = str(home / ".agents/skills/bulk-1/references/nested/GUIDE.md")
    _jsonl(
        home / ".gemini/antigravity-cli/brain/guide-task/.system_generated/logs/transcript.jsonl",
        [
            {"type": "USER_INPUT", "content": f"quoted path {home / '.agents/skills/bulk-2/references/guide.md'}"},
            {"tool_calls": [{"name": "read_file", "args": {"Path": alpha_guide}}]},
            {"tool_calls": [{"name": "read_file", "args": {"Path": _skill(home, "alpha")}}]},
            {"tool_calls": [{"name": "read_file", "args": {"Path": bulk_guide}}]},
            {"tool_calls": [{"name": "run_command", "args": {"CommandLine": f"cat {bulk_guide}"}}]},
        ],
    )
    _jsonl(
        home / ".claude/projects/-work-project/guide-session.jsonl",
        [
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": bulk_guide}}]},
            }
        ],
    )
    _jsonl(
        home / ".pi/agent/sessions/--work-project--/2026-11-10T10-00-00-000Z_pi-guide.jsonl",
        [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "toolCall",
                            "id": "c2",
                            "name": "read",
                            "arguments": {"path": "skills/bulk-1/references/guide.md"},
                        }
                    ],
                },
            }
        ],
    )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row for row in report["skills"]}

    assert report["sessions"] == {"agy": 3, "claude": 3, "pi": 2}
    assert by_skill["alpha"] == {"skill": "alpha", "agy": 2, "claude": 1, "pi": 0, "total": 3}
    assert by_skill["bulk-1"] == {"skill": "bulk-1", "agy": 1, "claude": 1, "pi": 1, "total": 3}
    assert by_skill["bulk-2"]["total"] == 0


def test_claude_non_session_files_and_pi_pre_fork_loads_are_excluded(tmp_path: Path) -> None:
    home = _home(tmp_path)
    claude = home / ".claude/projects/-work-project"
    for name in ("memory.jsonl", "journal.jsonl"):
        _jsonl(
            claude / name,
            [
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "bulk-3"}}]},
                }
            ],
        )
    _jsonl(
        home / ".pi/agent/sessions/--work-project--/2026-11-10T12-00-00-000Z_pi-fork.jsonl",
        [
            {
                "type": "session",
                "id": "pi-fork",
                "timestamp": "2026-11-10T12:00:00.000Z",
                "parentSession": "/work/parent.jsonl",
            },
            {
                "type": "message",
                "timestamp": "2026-11-10T11:59:59.000Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "toolCall",
                            "id": "copied",
                            "name": "read",
                            "arguments": {"path": "skills/bulk-4/SKILL.md"},
                        }
                    ],
                },
            },
            {
                "type": "message",
                "timestamp": "2026-11-10T12:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "toolCall",
                            "id": "fresh",
                            "name": "read",
                            "arguments": {"path": "skills/bulk-5/SKILL.md"},
                        }
                    ],
                },
            },
        ],
    )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row for row in report["skills"]}

    assert report["sessions"] == {"agy": 2, "claude": 2, "pi": 2}
    assert by_skill["bulk-3"]["total"] == 0
    assert by_skill["bulk-4"]["total"] == 0
    assert by_skill["bulk-5"] == {"skill": "bulk-5", "agy": 0, "claude": 0, "pi": 1, "total": 1}


def test_scripts_and_templates_reads_count_and_recent_unloaded_skills_are_flagged(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    home = _home(tmp_path)
    today = datetime.now(tz=UTC).date().isoformat()
    (home / ".agents/skills/bulk-6/SKILL.md").write_text(
        f'---\nname: bulk-6\nmetadata:\n  created: "{today}"\n---\n',
        encoding="utf-8",
    )
    script_path = str(home / ".agents/skills/bulk-2/scripts/run.py")
    tmpl_path = str(home / ".agents/skills/bulk-3/templates/card.typ")
    _jsonl(
        home / ".gemini/antigravity-cli/brain/asset-task/.system_generated/logs/transcript.jsonl",
        [
            {"tool_calls": [{"name": "read_file", "args": {"Path": script_path}}]},
            {"tool_calls": [{"name": "read_file", "args": {"Path": _skill(home, "bulk-2")}}]},
        ],
    )
    _jsonl(
        home / ".pi/agent/sessions/--work-project--/2026-11-12T10-00-00-000Z_pi-tmpl.jsonl",
        [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "toolCall", "id": "t1", "name": "read", "arguments": {"path": tmpl_path}}],
                },
            }
        ],
    )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row for row in report["skills"]}
    assert by_skill["bulk-2"] == {"skill": "bulk-2", "agy": 1, "claude": 0, "pi": 0, "total": 1}
    assert by_skill["bulk-3"] == {"skill": "bulk-3", "agy": 0, "claude": 0, "pi": 1, "total": 1}
    assert by_skill["bulk-6"]["total"] == 0

    text_out = _run(home).stdout
    assert f"bulk-6(new:{today})" in text_out
