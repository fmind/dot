from __future__ import annotations

import io
import json
import os
import signal
import sys
from pathlib import Path

import pytest

from fmind_dot import cli as cli_module
from fmind_dot.cli import app, build_parser
from fmind_dot.command import COMPLETE_VARIABLE, FISH_COMPLETION, candidates
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import CommandResult
from fmind_dot.reporting import diagnostic_report, display_path, write_json, write_report_line
from fmind_dot.state import State, require_tools, validated_config
from tests.fakes import CliRunner, ScriptedRunner, TerminalIO


def test_parser_tree_help_and_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()
    assert set(parser.children) == {
        "context",
        "doctor",
        "login",
        "pull",
        "stats",
        "status",
        "trust",
    }
    assert "__dot_prepare_candidates" in FISH_COMPLETION

    ver = CliRunner().invoke(app, ["--version"])
    assert ver.exit_code == 0
    assert "dot version" in ver.stdout
    monkeypatch.setenv("HOME", str(tmp_path))
    help_res = CliRunner().invoke(app, [])
    assert help_res.exit_code == 0
    assert "stats" in help_res.stdout
    assert "context" in help_res.stdout


def test_state_probe_caching_validation_and_require_tools(tmp_path: Path) -> None:
    calls = 0

    def run(cmd: list[str], *_a: object) -> CommandResult:
        nonlocal calls
        calls += 1
        return CommandResult(cmd[0], "", 0)

    state = State(runner=ScriptedRunner({"git"}, run=run))
    assert state.run_probe(("a",), lambda: state.runner.run(["a"])).stdout == "a"
    assert state.run_probe(("a",), lambda: state.runner.run(["a"])).stdout == "a"
    assert calls == 1
    state.clear_probes()
    assert state.run_probe(("a",), lambda: state.runner.run(["a"])).stdout == "a"
    assert calls == 2

    def fail() -> CommandResult:
        raise DotError("probe boom")

    with pytest.raises(DotError, match="probe boom"):
        state.run_probe(("b",), fail)
    with pytest.raises(DotError, match="probe boom"):
        state.run_probe(("b",), lambda: CommandResult("ok", "", 0))

    bad = tmp_path / "dot.yaml"
    bad.write_text("schema_version: 99\n", encoding="utf-8")
    with pytest.raises(DotError, match="validation error"):
        validated_config(bad)

    with pytest.raises(DotError, match="required tools are missing: a, z"):
        require_tools(state, [["z"], ["a"], ["git"]])


def test_reporting_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    monkeypatch.setattr(
        "fmind_dot.reporting.shutil.get_terminal_size", lambda fallback=(88, 24): os.terminal_size((40, fallback[1]))
    )
    long_id = "sub/" + "segment-" * 6 + "end"
    write_report_line(out, f"Path {long_id}")
    assert long_id in out.getvalue()

    monkeypatch.setenv("HOME", str(tmp_path))
    assert display_path(str(tmp_path / "sub/file")) == "~/sub/file"
    assert display_path("/var/other") == "/var/other"

    buf, tty = io.StringIO(), TerminalIO()
    write_json(buf, {"a": 1, "b": 2})
    write_json(tty, {"a": 1, "b": 2})
    assert buf.getvalue() == '{"a":1,"b":2}\n'
    assert "\n" in tty.getvalue().strip()

    rep = diagnostic_report("workstation", [{"name": "t", "status": "pass"}, {"name": "x", "status": "fail"}])
    assert (rep["schema"], rep["scope"], rep["passed"]) == ("dot.diagnostics/v1", "workstation", False)


def test_command_candidates_cover_commands_flags_values_and_double_dash() -> None:
    parser = build_parser()
    top = {v for v, _ in candidates(parser, [""])}
    assert top == {"context", "doctor", "login", "pull", "stats", "status", "trust"}
    flags = {v for v, _ in candidates(parser, ["status", "--"])}
    assert {"--json", "--fetch", "--needs-attention"} <= flags
    eq_vals = [v for v, _ in candidates(parser, ["login", "gcp", "--config="])]
    assert eq_vals == []
    assert {"colab", "gcp", "github", "workspace"} == {v for v, _ in candidates(parser, ["login", ""])}
    assert candidates(parser, ["status", "--", "a"]) == []
    assert [v for v, _ in candidates(parser, ["stats", "--agent", "c"])] == ["claude", "codex", "copilot"]
    assert [v for v, _ in candidates(parser, ["stats", "--agent=a"])] == ["--agent=agy"]


@pytest.mark.parametrize(
    ("exc", "expected_code", "err_match"),
    [
        (DotError("broken"), 1, "dot: broken\n"),
        (KeyboardInterrupt(), 130, "Cancelled.\n"),
        (BrokenPipeError(), 141, ""),
    ],
)
def test_main_exit_codes_and_complete_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exc: BaseException,
    expected_code: int,
    err_match: str,
) -> None:
    seen_sig: list[object] = []

    def fail_app() -> None:
        seen_sig.append(signal.getsignal(signal.SIGTERM))
        raise exc

    monkeypatch.delenv(COMPLETE_VARIABLE, raising=False)
    monkeypatch.setattr(cli_module, "app", fail_app)
    with pytest.raises(SystemExit) as stopped:
        cli_module.main()
    assert callable(seen_sig[0])
    assert stopped.value.code == expected_code
    assert err_match in capsys.readouterr().err

    monkeypatch.setenv(COMPLETE_VARIABLE, "st")
    monkeypatch.setattr(sys, "argv", ["dot"])
    cli_module.main()
    assert "status\t" in capsys.readouterr().out

    def bad_usage(_s: State, _a: object) -> None:
        raise UsageError("bad combination")

    parser = build_parser()
    monkeypatch.setattr(cli_module, "build_parser", lambda: parser)
    parser.children["status"].set_defaults(handler=bad_usage)
    res = CliRunner().invoke(app, ["status"])
    assert res.exit_code == 2
    assert "bad combination" in res.stderr
    monkeypatch.delenv(COMPLETE_VARIABLE, raising=False)
    monkeypatch.setattr(cli_module, "app", lambda: signal.raise_signal(signal.SIGTERM))
    with pytest.raises(SystemExit) as sig:
        cli_module.main()
    assert sig.value.code == 130
    assert json.loads('{"ok":true}')["ok"] is True
