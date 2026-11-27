from __future__ import annotations

import io
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from fmind_dot import __version__
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
        "privacy",
        "pull",
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
    assert "doctor" in help_res.stdout
    assert "context" in help_res.stdout

    env = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    mod_res = subprocess.run(
        [sys.executable, "-m", "fmind_dot", "--version"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert mod_res.returncode == 0, mod_res.stderr
    assert mod_res.stdout == f"dot version {__version__}\n"


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


def test_state_run_probe_singleflight_and_clear_generation_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    started = threading.Event()
    release = threading.Event()
    waiter_blocked = threading.Event()
    count = 0

    def slow_probe() -> CommandResult:
        nonlocal count
        count += 1
        started.set()
        release.wait(timeout=5)
        return CommandResult(f"run-{count}", "", 0)

    state = State(runner=ScriptedRunner())
    results: list[str] = []
    t1 = threading.Thread(target=lambda: results.append(state.run_probe(("k",), slow_probe).stdout))
    t1.start()
    assert started.wait(timeout=5)
    inflight_event = state._inflight[("k",)]  # noqa: SLF001
    real_wait = inflight_event.wait

    def instrumented_wait(timeout: float | None = None) -> bool:
        waiter_blocked.set()
        return real_wait(timeout)

    monkeypatch.setattr(inflight_event, "wait", instrumented_wait)
    t2 = threading.Thread(target=lambda: results.append(state.run_probe(("k",), slow_probe).stdout))
    t2.start()
    assert waiter_blocked.wait(timeout=5)
    release.set()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert count == 1
    assert results == ["run-1", "run-1"]

    # When the leading probe raises a cached DotError, waiting callers wake cleanly and see the same error without re-running.
    started.clear()
    release.clear()
    waiter_blocked.clear()
    state.clear_probes()
    err_calls = 0

    def failing_probe() -> CommandResult:
        nonlocal err_calls
        err_calls += 1
        started.set()
        release.wait(timeout=5)
        raise DotError("probe boom")

    errors: list[str] = []

    def run_err() -> None:
        try:
            state.run_probe(("err",), failing_probe)
        except DotError as exc:
            errors.append(str(exc))

    t_err1 = threading.Thread(target=run_err)
    t_err1.start()
    assert started.wait(timeout=5)
    err_event = state._inflight[("err",)]  # noqa: SLF001
    real_err_wait = err_event.wait

    def instrumented_err_wait(timeout: float | None = None) -> bool:
        waiter_blocked.set()
        return real_err_wait(timeout)

    monkeypatch.setattr(err_event, "wait", instrumented_err_wait)
    t_err2 = threading.Thread(target=run_err)
    t_err2.start()
    assert waiter_blocked.wait(timeout=5)
    release.set()
    t_err1.join(timeout=5)
    t_err2.join(timeout=5)
    assert err_calls == 1
    assert errors == ["probe boom", "probe boom"]

    # When the leading probe raises an uncached RuntimeError, waiting callers wake cleanly and retry.
    started.clear()
    release.clear()
    waiter_blocked.clear()
    crash_calls = 0
    crash_errors: list[str] = []
    recovered: list[str] = []

    def crashing_probe() -> CommandResult:
        nonlocal crash_calls
        crash_calls += 1
        if crash_calls == 1:
            started.set()
            release.wait(timeout=5)
            raise RuntimeError("transient crash")
        return CommandResult("recovered", "", 0)

    def run_crash() -> None:
        try:
            recovered.append(state.run_probe(("crash",), crashing_probe).stdout)
        except RuntimeError as exc:
            crash_errors.append(str(exc))

    t_cr1 = threading.Thread(target=run_crash)
    t_cr1.start()
    assert started.wait(timeout=5)
    cr_event = state._inflight[("crash",)]  # noqa: SLF001
    real_cr_wait = cr_event.wait

    def instrumented_cr_wait(timeout: float | None = None) -> bool:
        waiter_blocked.set()
        return real_cr_wait(timeout)

    monkeypatch.setattr(cr_event, "wait", instrumented_cr_wait)
    t_cr2 = threading.Thread(target=run_crash)
    t_cr2.start()
    assert waiter_blocked.wait(timeout=5)
    release.set()
    t_cr1.join(timeout=5)
    t_cr2.join(timeout=5)
    assert crash_errors == ["transient crash"]
    assert recovered == ["recovered"]

    # Calling clear_probes() while a probe is in-flight prevents stale write-back.
    started.clear()
    release.clear()
    state.clear_probes()
    stale_out: list[str] = []
    t3 = threading.Thread(target=lambda: stale_out.append(state.run_probe(("k",), slow_probe).stdout))
    t3.start()
    assert started.wait(timeout=5)
    state.clear_probes()
    release.set()
    t3.join(timeout=5)
    assert stale_out == ["run-2"]
    assert state.run_probe(("k",), lambda: CommandResult("fresh", "", 0)).stdout == "fresh"


def test_malformed_config_allows_config_free_commands_and_fails_config_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil
    from types import SimpleNamespace

    from fmind_dot import system as system_module

    monkeypatch.setenv("HOME", str(tmp_path))
    bad_cfg = tmp_path / ".config/dot.yaml"
    bad_cfg.parent.mkdir(parents=True)
    bad_cfg.write_text("schema_version: 999\n", encoding="utf-8")
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=200 * 1024**3))
    monkeypatch.setattr(system_module, "available_memory_bytes", lambda: 8 * 1024**3)

    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert runner.invoke(app, ["doctor", "--headroom", "--json"]).exit_code == 0
    assert runner.invoke(app, ["context", "--project", str(clean_dir), "--json"]).exit_code == 0
    assert runner.invoke(app, ["-c", str(tmp_path / "missing-for-other"), "--help"]).exit_code == 0

    bad_yaml_syntax = tmp_path / "broken.yaml"
    bad_yaml_syntax.write_text("pull: [\n", encoding="utf-8")
    for argv in (
        ["-c", str(bad_yaml_syntax), "doctor"],
        ["-c", str(bad_yaml_syntax), "status"],
        ["-c", str(bad_yaml_syntax), "pull"],
        ["-c", str(bad_yaml_syntax), "trust", str(clean_dir)],
        ["-c", str(bad_yaml_syntax), "login", "--check"],
    ):
        assert runner.invoke(app, argv).exit_code == 1, argv

    # privacy runs without dot.yaml schema validation (only parses mappings for private tokens).
    bad_cfg.unlink()
    assert runner.invoke(app, ["privacy", "--json", str(clean_dir)]).exit_code == 0


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
    assert top == {"context", "doctor", "login", "privacy", "pull", "status", "trust"}
    flags = {v for v, _ in candidates(parser, ["status", "--"])}
    assert {"--json", "--fetch", "--needs-attention"} <= flags
    privacy_flags = {v for v, _ in candidates(parser, ["privacy", "--"])}
    assert {"--json", "--quiet", "--staged"} <= privacy_flags
    eq_vals = [v for v, _ in candidates(parser, ["login", "gcp", "--config="])]
    assert eq_vals == []
    assert {"gcp", "github", "workspace"} == {v for v, _ in candidates(parser, ["login", ""])}
    assert {"gcp", "github", "workspace"} == {v for v, _ in candidates(parser, ["login", "--check", ""])}
    assert candidates(parser, ["status", "--", "a"]) == []
    for cmd in ("doctor", "context", "privacy"):
        short_flags = {v for v, _ in candidates(parser, [cmd, "-"])}
        assert {"-q", "--quiet"} <= short_flags
        quiet_line = parser.children[cmd].format_help().split("--quiet", 1)[1].splitlines()[0]
        assert "--json" in quiet_line
    for name, child in parser.children.items():
        help_text = child.format_help()
        assert "Examples:" in help_text, f"{name} --help missing Examples:"


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


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_main_closed_stdout_pipe_help_version_and_dot_error_exit_141(flag: str) -> None:
    env = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    proc = subprocess.Popen(
        [sys.executable, "-m", "fmind_dot", flag],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    proc.stdout.close()
    _out, err = proc.communicate(timeout=5)
    assert proc.returncode == 141
    assert err == b""


@pytest.mark.parametrize("exc_expr", ["cli.DotError('boom')", "KeyboardInterrupt()"])
def test_main_closed_stdout_pipe_errors_and_fileno_suppression(exc_expr: str, monkeypatch: pytest.MonkeyPatch) -> None:
    env = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    code = (
        "import sys; from fmind_dot import cli; "
        f"cli.app = lambda: (sys.stdout.write('partial\\n'), (_ for _ in ()).throw({exc_expr})); cli.main()"
    )
    proc = subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    proc.stdout.close()
    _out, err = proc.communicate(timeout=5)
    assert proc.returncode == 141
    assert err == b""

    class BrokenStreamNoFileno:
        def write(self, _text: str) -> int:
            raise BrokenPipeError

        def flush(self) -> None:
            raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", BrokenStreamNoFileno())
    monkeypatch.setattr(cli_module, "app", lambda: sys.stdout.write("x"))
    with pytest.raises(SystemExit) as stopped:
        cli_module.main()
    assert stopped.value.code == 141
