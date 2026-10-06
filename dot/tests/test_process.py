from __future__ import annotations

import os
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from threading import Thread
from unittest.mock import Mock

import pytest

from fmind_dot import process as process_module
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.process import CommandResult, Runner


@pytest.mark.parametrize("mode", ["captured", "interactive", "pull-worker", "status-worker", "doctor-worker"])
def test_sigterm_exits_130_and_stops_child_before_delayed_side_effect(mode: str, tmp_path: Path) -> None:
    started = tmp_path / "started"
    release = tmp_path / "release"
    finished = tmp_path / "finished"
    child = (
        "import pathlib,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text('started')\n"
        "deadline=time.monotonic()+30\n"
        "while not pathlib.Path(sys.argv[3]).exists():\n"
        " if time.monotonic()>deadline: raise SystemExit(0)\n"
        " time.sleep(0.01)\n"
        "pathlib.Path(sys.argv[2]).write_text('finished')\n"
    )
    launcher = (
        "import os,sys\n"
        "import fmind_dot.cli as cli\n"
        "import fmind_dot.repository as repository\n"
        "import fmind_dot.system as system\n"
        "from fmind_dot.config import Config\n"
        "from fmind_dot.state import State\n"
        "from pathlib import Path\n"
        "from fmind_dot.process import Runner\n"
        "command=[sys.executable,'-c',os.environ['DOT_CHILD'],os.environ['DOT_STARTED'],os.environ['DOT_FINISHED'],os.environ['DOT_RELEASE']]\n"
        "def invoke():\n"
        " runner=Runner()\n"
        " if os.environ['DOT_MODE']=='captured': runner.run(command)\n"
        " elif os.environ['DOT_MODE']=='pull-worker':\n"
        "  repository.find_git_repositories=lambda *_args: [Path('.')]\n"
        "  repository._pull_repository=lambda *_args,**_kwargs: runner.run(command)\n"
        "  repository.run_pull(State(runner=runner))\n"
        " elif os.environ['DOT_MODE']=='status-worker':\n"
        "  repository.find_git_repositories=lambda *_args: [Path('.')]\n"
        "  repository._repository_status=lambda *_args: runner.run(command)\n"
        "  repository.gather_status(State(runner=runner))\n"
        " elif os.environ['DOT_MODE']=='doctor-worker':\n"
        "  runner.which=lambda _tool: Path(sys.executable)\n"
        "  run=runner.run\n"
        "  runner.run=lambda _args,**kwargs: run(command,**kwargs)\n"
        "  state=State(runner=runner)\n"
        "  state._config=Config()\n"
        "  state.config.doctor.tools=['fixture']\n"
        "  system._tool_results(state)\n"
        " else: runner.interactive(command)\n"
        " return 0\n"
        "cli._invoke_app=invoke\n"
        "cli.main()\n"
    )
    environment = os.environ.copy()
    environment.update(
        {
            "DOT_CHILD": child,
            "DOT_FINISHED": str(finished),
            "DOT_MODE": mode,
            "DOT_RELEASE": str(release),
            "DOT_STARTED": str(started),
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-c", launcher],
        cwd=Path(__file__).parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Two interpreter startups plus CLI imports can exceed 5s under xdist load; the
        # wait ends as soon as the child is ready, so a generous deadline costs nothing.
        deadline = time.monotonic() + 30
        while not started.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert started.exists(), f"child did not become ready (launcher exit: {process.poll()})"

        process.send_signal(process_module.signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=5)
        # Only permit the side effect after cancellation returned; host scheduling
        # cannot let a short timer fire before this test delivers SIGTERM.
        release.touch()
        time.sleep(0.1)

        assert process.returncode == 130
        assert stdout == ""
        assert stderr == "Cancelled.\n"
        assert not finished.exists()
    finally:
        # Startup/assertion failures must not leak a child or pipe handles into
        # later tests; cancellation timing is still asserted above.
        if process.poll() is None:
            release.touch()
            process.terminate()
        process.communicate(timeout=5)


def test_runner_validates_commands() -> None:
    runner = Runner()

    assert runner.which(sys.executable) == Path(sys.executable)
    assert runner.which("fmind-dot-command-that-does-not-exist") is None
    with pytest.raises(DotError, match="empty command"):
        runner.run([])
    with pytest.raises(DotError, match="empty command"):
        runner.interactive([])


def test_cancel_prohibits_subsequent_worker_commands(tmp_path: Path) -> None:
    runner = Runner()
    runner.cancel()
    with pytest.raises(DotError, match="cancelled"):
        runner.run([sys.executable, "-c", "from pathlib import Path; Path('should-not-exist').touch()"], cwd=tmp_path)
    assert not (tmp_path / "should-not-exist").exists()


def test_cancellation_during_launch_reports_cancellation_and_reaps_child(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Runner()
    popen = subprocess.Popen
    children: list[subprocess.Popen[str] | subprocess.Popen[bytes]] = []

    def launch(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        # Cancellation lands after the OS launch, before Runner registers the child.
        runner.cancel()
        return child

    monkeypatch.setattr(process_module.subprocess, "Popen", launch)
    try:
        with pytest.raises(DotError, match="operation cancelled"):
            runner.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=2)
        assert children[0].poll() is not None
        assert children[0].stdout is not None
        assert children[0].stdout.closed
        assert children[0].stderr is not None
        assert children[0].stderr.closed
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    stream.close()


def test_run_preserves_cwd_input_and_environment_and_redacts_failures(tmp_path: Path) -> None:
    script = (
        "import os,pathlib,sys\n"
        "print(pathlib.Path.cwd().name)\n"
        "print(os.environ['DOT_PROCESS_TEST'])\n"
        "print(sys.stdin.read())\n"
        "print('provider-secret', file=sys.stderr)\n"
        "raise SystemExit(7)\n"
    )
    runner = Runner()

    result = runner.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        input_text="payload",
        env={"DOT_PROCESS_TEST": "present"},
        check=False,
    )

    assert result.returncode == 7
    assert result.stdout.splitlines() == [tmp_path.name, "present", "payload"]
    assert result.stderr == "provider-secret\n"
    with pytest.raises(DotError, match=r"command failed \(7\)") as raised:
        runner.run(
            [sys.executable, "-c", script], cwd=tmp_path, input_text="payload", env={"DOT_PROCESS_TEST": "present"}
        )
    assert "provider-secret" not in str(raised.value)


def test_interactive_preserves_cwd_and_environment(tmp_path: Path) -> None:
    result_path = tmp_path / "result"
    code = Runner().interactive(
        [
            sys.executable,
            "-c",
            "import os,pathlib; pathlib.Path('result').write_text(os.environ['DOT_INTERACTIVE_TEST']); raise SystemExit(6)",
        ],
        cwd=tmp_path,
        env={"DOT_INTERACTIVE_TEST": "present"},
    )

    assert code == 6
    assert result_path.read_text(encoding="utf-8") == "present"


def test_run_streams_large_input_and_delivers_empty_input_eof() -> None:
    payload = "x" * (256 * 1024)
    reader = "import sys; value=sys.stdin.read(); print(len(value))"

    large = Runner().run([sys.executable, "-c", reader], input_text=payload, timeout=5)
    empty = Runner().run([sys.executable, "-c", reader], input_text="", timeout=5)

    assert large.stdout == f"{len(payload)}\n"
    assert empty.stdout == "0\n"


def test_run_tolerates_child_closing_stdin_early() -> None:
    result = Runner().run(
        [sys.executable, "-c", "import os,time; os.close(0); time.sleep(.05)"],
        input_text="x" * (1024 * 1024),
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_run_applies_universal_newlines() -> None:
    script = "import os; os.write(1, b'a\\r\\nb\\rc')"
    assert Runner().run([sys.executable, "-c", script]).stdout == "a\nb\nc"


def test_run_replaces_invalid_locale_bytes() -> None:
    script = "import os; os.write(1, b'ok\\xff\\n'); os.write(2, b'\\xfe')"

    result = Runner().run([sys.executable, "-c", script])

    assert result.stdout == "ok�\n"
    assert result.stderr == "�"


_TERM_CHILD = (
    "import pathlib,signal,sys,time\n"
    "def stop(*_): pathlib.Path(sys.argv[2]).write_text('clean'); raise SystemExit(0)\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN if sys.argv[3]=='ignore' else stop)\n"
    "pathlib.Path(sys.argv[1]).write_text(str(__import__('os').getpid()))\n"
    "time.sleep(30)\n"
)


def _wait_for(path: Path) -> None:
    # Readiness waits end as soon as the child is up, so a load-tolerant deadline costs nothing.
    deadline = time.monotonic() + 30
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert path.exists(), "child did not become ready before the startup deadline"


def test_timeout_lets_child_handle_sigterm_before_kill(tmp_path: Path) -> None:
    ready, clean = tmp_path / "ready", tmp_path / "clean"

    with pytest.raises(CommandTimeoutError, match="command timed out"):
        Runner().run([sys.executable, "-c", _TERM_CHILD, str(ready), str(clean), "trap"], timeout=0.75)

    assert ready.exists(), "child did not install its handler before the timeout"
    assert clean.read_text() == "clean"


@pytest.mark.parametrize("group_error", [None, ProcessLookupError, PermissionError])
def test_cancel_lets_child_handle_sigterm_before_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group_error: type[OSError] | None
) -> None:
    if group_error is not None:
        monkeypatch.setattr(process_module.os, "killpg", Mock(side_effect=group_error))
    ready, clean = tmp_path / "ready", tmp_path / "clean"
    runner = Runner()
    results: list[CommandResult] = []
    worker = Thread(
        target=lambda: results.append(
            runner.run([sys.executable, "-c", _TERM_CHILD, str(ready), str(clean), "trap"], check=False)
        )
    )
    worker.start()
    try:
        _wait_for(ready)
        runner.cancel()
    finally:
        worker.join(timeout=10)

    assert not worker.is_alive()
    assert clean.read_text() == "clean"
    assert [result.returncode for result in results] == [0]


@pytest.mark.parametrize("stop", ["timeout", "cancel"])
@pytest.mark.parametrize("group_error", [None, ProcessLookupError, PermissionError])
def test_child_ignoring_sigterm_is_killed_after_bounded_grace(
    stop: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group_error: type[OSError] | None
) -> None:
    if group_error is not None:
        monkeypatch.setattr(process_module.os, "killpg", Mock(side_effect=group_error))
    monkeypatch.setattr(process_module, "_TERMINATION_GRACE_SECONDS", 0.3)
    ready, clean = tmp_path / "ready", tmp_path / "clean"
    command = [sys.executable, "-c", _TERM_CHILD, str(ready), str(clean), "ignore"]
    runner = Runner()
    results: list[CommandResult] = []

    # The timeout must outlast interpreter startup on a loaded host, or the child dies
    # before writing its pid; the bound still rejects the 2-second default grace.
    timeout = 3.0
    if stop == "timeout":
        started = time.monotonic()
        with pytest.raises(DotError, match="command timed out"):
            runner.run(command, timeout=timeout)
    else:
        worker = Thread(target=lambda: results.append(runner.run(command, check=False)))
        worker.start()
        try:
            _wait_for(ready)
            started = time.monotonic()
            runner.cancel()
        finally:
            worker.join(timeout=10)
        assert not worker.is_alive()
        assert [result.returncode for result in results] == [-process_module.signal.SIGKILL]

    assert time.monotonic() - started < (timeout + 1.5 if stop == "timeout" else 4)
    assert not clean.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(int(ready.read_text()), 0)


def test_timeout_is_bounded_when_descendant_escapes_process_group() -> None:
    escaped_child = (
        "import os,time\n"
        "deadline=time.monotonic()+3\n"
        "while time.monotonic()<deadline:\n"
        " try: os.write(1,b'x')\n"
        " except BrokenPipeError: break\n"
        " time.sleep(.05)\n"
    )
    parent = (
        "import subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable,'-c',{escaped_child!r}],start_new_session=True)\n"
        "time.sleep(30)\n"
    )

    started = time.monotonic()
    with pytest.raises(DotError, match="command timed out"):
        Runner().run([sys.executable, "-c", parent], timeout=0.1)

    assert time.monotonic() - started < 1.5


def test_timeout_is_bounded_for_silent_process() -> None:
    started = time.monotonic()
    with pytest.raises(DotError, match="command timed out"):
        Runner().run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.05)

    assert time.monotonic() - started < 1.5


def test_keyboard_interrupt_terminates_child_and_closes_capture_pipes(monkeypatch: pytest.MonkeyPatch) -> None:
    class InterruptedProcess:
        def __init__(self) -> None:
            self.pid = 424_242
            self.stdin = StringIO()
            self.stdout = StringIO()
            self.stderr = StringIO()
            self.returncode = 0
            self.waited = False

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.returncode = -9

        def wait(self, timeout: float | None) -> int:
            del timeout
            self.waited = True
            return self.returncode

        def communicate(self, *_args: object, **_kwargs: object) -> tuple[str, str]:
            raise KeyboardInterrupt

    process = InterruptedProcess()
    signals: list[tuple[int, int]] = []

    def popen(*args: object, **kwargs: object) -> InterruptedProcess:
        del args, kwargs
        return process

    monkeypatch.setattr(process_module.subprocess, "Popen", popen)
    monkeypatch.setattr(process_module.os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        Runner().run(["command"])

    assert process.waited
    assert signals == [(process.pid, process_module.signal.SIGTERM), (process.pid, process_module.signal.SIGKILL)]
    assert process.stdin.closed
    assert process.stdout.closed
    assert process.stderr.closed


def test_interactive_child_restores_default_interrupt_and_reports_it() -> None:
    previous = process_module.signal.getsignal(process_module.signal.SIGINT)
    # dot defers Ctrl+C to the child; an inherited SIG_IGN would make the child immune to it.
    inherited = "import signal,sys; sys.exit(0 if signal.getsignal(signal.SIGINT) is signal.default_int_handler else 9)"
    interrupted = "import os,signal; signal.signal(signal.SIGINT, signal.SIG_DFL); os.kill(os.getpid(), signal.SIGINT)"

    assert Runner().interactive([sys.executable, "-c", inherited]) == 0
    with pytest.raises(KeyboardInterrupt):
        Runner().interactive([sys.executable, "-c", interrupted])
    assert process_module.signal.getsignal(process_module.signal.SIGINT) is previous


def test_interactive_relay_echoes_stderr_lines_and_reports_each() -> None:
    lines: list[str] = []
    stderr = StringIO()
    script = "import sys; sys.stderr.write('Open this URL:\\n  https://example.test\\n'); sys.exit(3)"
    with Path(os.devnull).open(encoding="utf-8") as stdin:
        code = Runner().interactive(
            [sys.executable, "-c", script], stdin=stdin, stderr=stderr, on_stderr_line=lines.append
        )
    assert code == 3
    assert lines == ["Open this URL:\n", "  https://example.test\n"]
    assert stderr.getvalue() == "".join(lines)


def test_interactive_relay_returns_while_an_escaped_descendant_holds_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process_module, "_TERMINATION_TIMEOUT_SECONDS", 0.2)
    lines: list[str] = []
    started = time.monotonic()
    # The background sleep inherits the stderr pipe and outlives the shell.
    code = Runner().interactive(
        ["sh", "-c", "echo ready >&2; sleep 5 & exit 0"], stderr=StringIO(), on_stderr_line=lines.append
    )
    assert code == 0
    assert time.monotonic() - started < 3
    assert lines == ["ready\n"]


def test_sigterm_stops_descendants_of_a_child_without_a_terminal(tmp_path: Path) -> None:
    pid_file = tmp_path / "descendant.pid"
    launcher = (
        "import signal,sys\n"
        "from fmind_dot.cli import _interrupt_on_sigterm\n"
        "from fmind_dot.process import Runner\n"
        "signal.signal(signal.SIGTERM, _interrupt_on_sigterm)\n"
        "try:\n"
        f" Runner().interactive(['sh','-c','sleep 30 & echo $! > {pid_file}; wait'])\n"
        "except KeyboardInterrupt:\n"
        " sys.exit(130)\n"
    )
    # Supervisors and CI give dot no terminal; the shell's background sleep must not outlive it.
    dot = subprocess.Popen(
        [sys.executable, "-c", launcher],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while not (pid_file.exists() and pid_file.read_text().strip()):
            assert time.monotonic() < deadline, "the child never started"
            time.sleep(0.02)
        descendant = int(pid_file.read_text())
        dot.terminate()
        assert dot.wait(timeout=30) == 130
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(descendant, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            os.kill(descendant, process_module.signal.SIGKILL)
            pytest.fail("the descendant survived SIGTERM to dot")
    finally:
        if dot.poll() is None:
            dot.kill()
            dot.wait()
