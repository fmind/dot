"""Unit tests for the on-demand supagent live calibration runner."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from dot_tasks import calibrate_supagents as cal
from fmind_dot.errors import CommandTimeoutError
from fmind_dot.process import CommandResult


def _fake_payload(
    *,
    verdict: str = "PASS",
    findings: list[dict[str, Any]] | None = None,
    status: str = "SUCCESS",
    finished_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "finished_reason": finished_reason,
        "duration_seconds": 3.5,
        "structured_output": {
            "verdict": verdict,
            "summary": "fixture",
            "findings": findings or [],
            "deletions": [],
            "unverified": [],
        },
    }


def test_list_and_usage_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert cal.main(["--list", "--role", "code", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [c["kind"] for c in listed["cases"]] == ["defect", "clean", "unreadable"]

    assert cal.main(["--list", "--role", "fmind-review-shell"]) == 0
    assert "fmind-review-shell" in capsys.readouterr().out

    with pytest.raises(SystemExit) as bad_role:
        cal.main(["--role", "nonexistent"])
    assert bad_role.value.code == 2

    with pytest.raises(SystemExit) as bad_timeout:
        cal.main(["--timeout", "0"])
    assert bad_timeout.value.code == 2

    with pytest.raises(SystemExit) as bad_workers:
        cal.main(["--workers", "0"])
    assert bad_workers.value.code == 2


def test_evaluate_structured_output_enforces_defect_clean_and_unreadable_contracts() -> None:
    defect_case, clean_case, unreadable_case = cal.select_cases(["code"])

    # Case-insensitive exact match on blocking finding passes; prefix collision ("Rubric #10") or P2-only citation fails.
    good_defect = cal.evaluate_structured_output(
        defect_case,
        _fake_payload(verdict="BLOCK", findings=[{"severity": "P1", "id": "x", "rule": "rubric #1"}]),
        mutated=False,
    )
    assert good_defect.passed is True

    prefix_collision = cal.evaluate_structured_output(
        defect_case,
        _fake_payload(verdict="BLOCK", findings=[{"severity": "P1", "id": "x", "rule": "Rubric #10"}]),
        mutated=False,
    )
    assert prefix_collision.passed is False

    p2_only_rule = cal.evaluate_structured_output(
        defect_case,
        _fake_payload(
            verdict="BLOCK",
            findings=[
                {"severity": "P1", "id": "a", "rule": "doc:1"},
                {"severity": "P2", "id": "b", "rule": "Rubric #1"},
            ],
        ),
        mutated=False,
    )
    assert p2_only_rule.passed is False

    missed_defect = cal.evaluate_structured_output(defect_case, _fake_payload(verdict="PASS"), mutated=False)
    assert missed_defect.passed is False
    assert any("expected BLOCK or REVISE" in err for err in missed_defect.errors)

    clean_ok = cal.evaluate_structured_output(clean_case, _fake_payload(verdict="PASS"), mutated=False)
    assert clean_ok.passed is True

    clean_fp = cal.evaluate_structured_output(
        clean_case,
        _fake_payload(verdict="PASS", findings=[{"severity": "P2", "id": "nit", "rule": "Rubric #4"}]),
        mutated=False,
    )
    assert clean_fp.passed is False
    assert any("invented findings" in err for err in clean_fp.errors)

    unreadable_ok = cal.evaluate_structured_output(unreadable_case, _fake_payload(verdict="BLOCK"), mutated=False)
    assert unreadable_ok.passed is True

    unreadable_open = cal.evaluate_structured_output(unreadable_case, _fake_payload(verdict="PASS"), mutated=False)
    assert unreadable_open.passed is False
    assert any("failed open" in err for err in unreadable_open.errors)

    mutated = cal.evaluate_structured_output(clean_case, _fake_payload(verdict="PASS"), mutated=True)
    assert mutated.passed is False
    assert any("mutated" in err for err in mutated.errors)

    denied_payload = _fake_payload(verdict="PASS") | {"denied_actions": [{"tool": "run_command"}]}
    denied = cal.evaluate_structured_output(clean_case, denied_payload, mutated=False)
    assert denied.passed is False
    assert any("denied_actions" in err for err in denied.errors)

    assert unreadable_case.prompt_note == ""


def test_run_case_and_main_with_mock_executor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    compiled_dir = tmp_path / "agents"
    compiled_dir.mkdir()
    (compiled_dir / "fmind-review-code.md").write_text("---\nname: fmind-review-code\n---\n# Code\n", encoding="utf-8")

    seen_cmds: list[list[str]] = []

    def ok_executor(cmd: Sequence[str], _cwd: Path, _timeout: int) -> CommandResult:
        seen_cmds.append(list(cmd))
        prompt = cmd[-1]
        if "bad_writer.py" in prompt:
            payload = _fake_payload(
                verdict="BLOCK", findings=[{"severity": "P1", "id": "swallow", "rule": "Rubric #1"}]
            )
        elif "does_not_exist.py" in prompt:
            payload = _fake_payload(verdict="BLOCK")
        else:
            payload = _fake_payload(verdict="PASS")
        return CommandResult(stdout=json.dumps(payload), stderr="", returncode=0)

    assert cal.main(["--role", "code", "--workers", "2", "--json"], executor=ok_executor) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is True
    assert len(report["outcomes"]) == 3
    assert all(
        "--disable-slash-commands" in cmd
        and "--sandbox" in cmd
        and cmd[cmd.index("--model") : cmd.index("--model") + 4]
        == ["--model", "gemini-4-hydrogen", "--effort", "medium"]
        for cmd in seen_cmds
    )

    suffixed_cmds: list[list[str]] = []

    def capture_ok(cmd: Sequence[str], _cwd: Path, _timeout: int) -> CommandResult:
        suffixed_cmds.append(list(cmd))
        return CommandResult(stdout=json.dumps(_fake_payload(verdict="PASS")), stderr="", returncode=0)

    clean_case = cal.select_cases(["code"])[1]
    assert cal.run_case(
        clean_case, model="gemini-4-hydrogen-medium", compiled_dir=compiled_dir, executor=capture_ok
    ).passed
    assert "--effort" not in suffixed_cmds[-1]
    assert cal.run_case(clean_case, effort="low", compiled_dir=compiled_dir, executor=capture_ok).passed
    assert suffixed_cmds[-1][suffixed_cmds[-1].index("--model") : suffixed_cmds[-1].index("--model") + 4] == [
        "--model",
        "gemini-4-hydrogen",
        "--effort",
        "low",
    ]

    # Mutating executor (file edit, empty dir, dangling symlink, or mutation + error/timeout) fails closed and reports mutation.
    def mutating_executor(_cmd: Sequence[str], cwd: Path, _timeout: int) -> CommandResult:
        (cwd / "clean_math.py").write_text("# tampered\n", encoding="utf-8")
        return CommandResult(stdout=json.dumps(_fake_payload(verdict="PASS")), stderr="", returncode=0)

    outcome = cal.run_case(clean_case, compiled_dir=compiled_dir, executor=mutating_executor)
    assert outcome.passed is False
    assert any("mutated" in err for err in outcome.errors)

    def dir_symlink_executor(_cmd: Sequence[str], cwd: Path, _timeout: int) -> CommandResult:
        (cwd / "empty_dir").mkdir()
        (cwd / "dangling_link").symlink_to("/nonexistent/outside")
        return CommandResult(stdout=json.dumps(_fake_payload(verdict="PASS")), stderr="", returncode=0)

    sym_outcome = cal.run_case(clean_case, compiled_dir=compiled_dir, executor=dir_symlink_executor)
    assert sym_outcome.passed is False
    assert any("mutated" in err for err in sym_outcome.errors)

    def mutate_and_timeout(_cmd: Sequence[str], cwd: Path, _timeout: int) -> CommandResult:
        (cwd / "leaked.txt").write_text("x", encoding="utf-8")
        raise CommandTimeoutError("timed out")

    to_outcome = cal.run_case(clean_case, compiled_dir=compiled_dir, executor=mutate_and_timeout)
    assert to_outcome.passed is False
    assert any("mutated" in err for err in to_outcome.errors)
    assert any("timed out" in err for err in to_outcome.errors)

    def err_executor(_cmd: Sequence[str], _cwd: Path, _t: int) -> CommandResult:
        return CommandResult(stdout="", stderr="AGY_ERROR", returncode=3)

    assert cal.run_case(clean_case, compiled_dir=compiled_dir, executor=err_executor).passed is False

    def bad_json_executor(_cmd: Sequence[str], _cwd: Path, _t: int) -> CommandResult:
        return CommandResult(stdout="not-json", stderr="", returncode=0)

    assert cal.run_case(clean_case, compiled_dir=compiled_dir, executor=bad_json_executor).passed is False
    assert cal.run_case(clean_case, compiled_dir=tmp_path / "missing", executor=ok_executor).passed is False

    def interrupt_executor(_cmd: Sequence[str], _cwd: Path, _t: int) -> CommandResult:
        raise KeyboardInterrupt

    assert cal.main(["--role", "code", "--workers", "1"], executor=interrupt_executor) == 130


def test_run_case_real_runner_handles_nonzero_exit_and_preserves_mutation(tmp_path: Path) -> None:
    compiled_dir = tmp_path / "agents"
    compiled_dir.mkdir()
    (compiled_dir / "fmind-review-code.md").write_text("---\nname: fmind-review-code\n---\n# Code\n", encoding="utf-8")

    fake_agy = tmp_path / "fake-agy"
    fake_agy.write_text(
        "#!/bin/sh\nprintf 'tampered' > leaked.txt\nprintf 'AGY_ERROR\\n' >&2\nexit 3\n",
        encoding="utf-8",
    )
    fake_agy.chmod(0o755)

    clean_case = cal.select_cases(["code"])[1]
    outcome = cal.run_case(clean_case, agy_bin=str(fake_agy), compiled_dir=compiled_dir, timeout_seconds=10)
    assert outcome.passed is False
    assert any("mutated" in err for err in outcome.errors)
    assert any("agy exit 3" in err for err in outcome.errors)
