"""Count observed skill loads from synthetic agy transcripts."""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/skillify/scripts/skill_loads.py"
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
    _jsonl(
        agy / "task/.system_generated/logs/transcript_full.jsonl",
        [
            {"type": "USER_INPUT", "content": f"private prompt quoting {_skill(tmp_path, 'beta')}"},
            {"tool_calls": [{"name": "read_file", "args": {"AbsolutePath": _skill(tmp_path, "alpha")}}]},
            {"tool_calls": [{"name": "view_file", "args": {"AbsolutePath": _skill(tmp_path, "alpha")}}]},
            {"tool_calls": [{"name": "run_command", "args": {"CommandLine": f"cat {_skill(tmp_path, 'beta')}"}}]},
        ],
    )
    _jsonl(
        agy / "audit/.system_generated/logs/transcript.jsonl",
        [{"tool_calls": [{"name": "read_file", "args": {"AbsolutePath": _skill(tmp_path, name)}}]} for name in CATALOG],
    )
    return tmp_path


def test_counts_agy_loads_excludes_audits_and_keeps_transcript_private(tmp_path: Path) -> None:
    home = _home(tmp_path)
    res_json = _run(home, "--json")
    assert res_json.returncode == 0, res_json.stderr
    assert res_json.stderr == ""
    report = json.loads(res_json.stdout)
    assert report["schema"] == "skillify.skill-loads/v2"
    assert report["sessions"] == 2
    assert report["audit_sessions_excluded"] == 1
    assert report["skills"][0] == {"skill": "alpha", "loads": 1}
    assert all(row["loads"] == 0 for row in report["skills"][1:])

    res_text = _run(home)
    assert res_text.returncode == 0, res_text.stderr
    lines = res_text.stdout.splitlines()
    assert lines[0] == "Skill loads over 30 days · sessions: 2 · audits excluded: 1"
    assert lines[1] == "alpha  1"
    assert lines[2] == "No observed load (9): beta " + " ".join(f"bulk-{index}" for index in range(8))
    assert "private prompt" not in res_text.stdout


def test_window_and_bad_arguments(tmp_path: Path) -> None:
    home = _home(tmp_path)
    for path in home.rglob("*.jsonl"):
        os.utime(path, (0, 0))
    aged = json.loads(_run(home, "--json", "--days", "7").stdout)
    assert aged["sessions"] == 0
    assert _run(home, "--days", "0").returncode == 2
    missing = _run(home, "--skills", str(tmp_path / "missing"))
    assert missing.returncode == 2
    assert "no skills found" in missing.stderr


def test_subagent_rollups_compact_preference_and_resource_reads(tmp_path: Path) -> None:
    home = _home(tmp_path)
    app_dir = home / ".gemini/antigravity-cli"
    today = datetime.now(tz=UTC).date().isoformat()
    (home / ".agents/skills/bulk-6/SKILL.md").write_text(
        f'---\nname: bulk-6\nmetadata:\n  created: "{today}"\n---\n', encoding="utf-8"
    )
    # Child subagent rolls into root `task` (including cycle guard in DB).
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
    # Compact transcript takes precedence over transcript_full; scripts/references/assets count without double-counting.
    both_logs = app_dir / "brain/both/.system_generated/logs"
    _jsonl(
        both_logs / "transcript.jsonl",
        [
            {"tool_calls": [{"name": "read_file", "args": {"Path": json.dumps(_skill(home, "bulk-4"))}}]},
            {"tool_calls": [{"name": "read_file", "args": {"Path": str(home / ".agents/skills/bulk-1/scripts/x.py")}}]},
            {"tool_calls": [{"name": "read_file", "args": {"Path": str(home / ".agents/skills/bulk-1/assets/a.svg")}}]},
            {
                "tool_calls": [
                    {"name": "read_file", "args": {"Path": str(home / ".agents/skills/bulk-2/references/g.md")}}
                ]
            },
        ],
    )
    _jsonl(
        both_logs / "transcript_full.jsonl",
        [{"tool_calls": [{"name": "read_file", "args": {"Path": _skill(home, "bulk-5")}}]}],
    )

    report = json.loads(_run(home, "--json").stdout)
    by_skill = {row["skill"]: row["loads"] for row in report["skills"]}
    assert report["sessions"] == 3
    assert by_skill["alpha"] == 1
    assert by_skill["beta"] == 1
    assert by_skill["bulk-1"] == 1
    assert by_skill["bulk-2"] == 1
    assert by_skill["bulk-4"] == 1
    assert by_skill["bulk-5"] == 0
    assert f"bulk-6(new:{today})" in _run(home).stdout


def test_invalid_utf8_empty_and_unreadable_skills_are_handled_safely(tmp_path: Path) -> None:
    home = _home(tmp_path)
    agy = home / ".gemini/antigravity-cli/brain"
    bad_log = agy / "utf8/.system_generated/logs/transcript.jsonl"
    bad_log.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"tool_calls": [{"name": "view_file", "args": {"Path": _skill(home, "bulk-7")}}]}).encode()
    bad_log.write_bytes(line[:-1] + b',"raw":"\xff"}\n{"broken":\n')
    empty_log = agy / "empty/.system_generated/logs/transcript.jsonl"
    empty_log.parent.mkdir(parents=True, exist_ok=True)
    empty_log.write_bytes(b"")

    skills_dir = home / ".agents/skills"
    (skills_dir / "broken-dir/SKILL.md").mkdir(parents=True)
    unreadable = skills_dir / "unreadable-skill/SKILL.md"
    unreadable.parent.mkdir(parents=True)
    unreadable.write_text("---\nname: unreadable-skill\n---\n", encoding="utf-8")
    is_non_root = os.geteuid() != 0
    if is_non_root:
        unreadable.chmod(0o000)
    try:
        report = json.loads(_run(home, "--json").stdout)
        by_skill = {row["skill"]: row["loads"] for row in report["skills"]}
        assert by_skill["bulk-7"] == 1
        assert "broken-dir" not in by_skill
        assert "unreadable-skill" in by_skill
    finally:
        if is_non_root:
            unreadable.chmod(0o644)
