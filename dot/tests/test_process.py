from __future__ import annotations

import os
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from typing import cast

import pytest

from fmind_dot import process as process_module
from fmind_dot.errors import DotError
from fmind_dot.process import Runner


@pytest.mark.parametrize("mode", ["captured", "interactive"])
def test_sigterm_exits_130_and_stops_child_before_delayed_side_effect(mode: str, tmp_path: Path) -> None:
    started = tmp_path / "started"
    finished = tmp_path / "finished"
    child = (
        "import pathlib,sys,time\n"
        "pathlib.Path(sys.argv[1]).write_text('started')\n"
        "time.sleep(0.3)\n"
        "pathlib.Path(sys.argv[2]).write_text('finished')\n"
    )
    launcher = (
        "import os,sys\n"
        "import fmind_dot.cli as cli\n"
        "from fmind_dot.process import Runner\n"
        "command=[sys.executable,'-c',os.environ['DOT_CHILD'],os.environ['DOT_STARTED'],os.environ['DOT_FINISHED']]\n"
        "def invoke():\n"
        " runner=Runner()\n"
        " if os.environ['DOT_MODE']=='captured': runner.run(command)\n"
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
    deadline = time.monotonic() + 5
    while not started.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert started.exists(), process.communicate(timeout=1)

    process.send_signal(process_module.signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=5)
    time.sleep(0.4)

    assert process.returncode == 130
    assert stdout == ""
    assert stderr == ""
    assert not finished.exists()


def test_runner_validates_commands_and_output_budget() -> None:
    runner = Runner()

    assert runner.which(sys.executable) == Path(sys.executable)
    assert runner.which("fmind-dot-command-that-does-not-exist") is None
    with pytest.raises(DotError, match="empty command"):
        runner.run([])
    with pytest.raises(DotError, match="empty command"):
        runner.interactive([])
    with pytest.raises(DotError, match="captured output must be positive"):
        runner.run_bounded([sys.executable], max_output_bytes=0)


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


def test_bounded_capture_drains_oversized_stdout_and_stderr() -> None:
    output_bytes = 2 * 1024 * 1024
    script = f"import os\nos.write(1, b'o' * {output_bytes})\nos.write(2, b'e' * {output_bytes})\n"

    result = Runner().run_bounded([sys.executable, "-c", script], timeout=5, max_output_bytes=4096)

    assert result.returncode == 0
    assert len(result.stdout.encode()) + len(result.stderr.encode()) == 4096
    assert set(result.stdout) <= {"o"}
    assert set(result.stderr) <= {"e"}
    assert result.output_truncated
    assert result.stdout_truncated or result.stderr_truncated


def test_bounded_capture_preserves_small_output_and_input() -> None:
    script = "import sys; value=sys.stdin.read(); print(value); print('diagnostic', file=sys.stderr)"

    result = Runner().run_bounded(
        [sys.executable, "-c", script],
        input_text="payload",
        max_output_bytes=4096,
    )

    assert result.stdout == "payload\n"
    assert result.stderr == "diagnostic\n"
    assert not result.output_truncated


def test_bounded_capture_streams_large_input_and_delivers_empty_input_eof() -> None:
    payload = "x" * (256 * 1024)
    reader = "import sys; value=sys.stdin.read(); print(len(value))"

    large = Runner().run_bounded(
        [sys.executable, "-c", reader],
        input_text=payload,
        max_output_bytes=64,
        timeout=5,
    )
    empty = Runner().run_bounded(
        [sys.executable, "-c", reader],
        input_text="",
        max_output_bytes=64,
        timeout=5,
    )

    assert large.stdout == f"{len(payload)}\n"
    assert empty.stdout == "0\n"


def test_bounded_capture_tolerates_child_closing_stdin_early() -> None:
    result = Runner().run_bounded(
        [sys.executable, "-c", "import os,time; os.close(0); time.sleep(.05)"],
        input_text="x" * (1024 * 1024),
        max_output_bytes=64,
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_bounded_capture_replaces_invalid_locale_bytes() -> None:
    script = "import os; os.write(1, bytes([255, 254])); os.write(2, bytes([253]))"

    result = Runner().run_bounded([sys.executable, "-c", script], max_output_bytes=3)

    assert result.stdout == "��"
    assert result.stderr == "�"
    assert not result.output_truncated


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
        Runner().run_bounded([sys.executable, "-c", parent], timeout=0.1, max_output_bytes=64)

    assert time.monotonic() - started < 1.5


def test_timeout_is_bounded_for_silent_process() -> None:
    started = time.monotonic()
    with pytest.raises(DotError, match="command timed out"):
        Runner().run_bounded(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout=0.05,
            max_output_bytes=64,
        )

    assert time.monotonic() - started < 1.5


def test_termination_falls_back_when_process_group_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubbornProcess:
        def __init__(self) -> None:
            self.pid = 424_243
            self.stdin = StringIO()
            self.stdout = StringIO()
            self.stderr = StringIO()
            self.kills = 0
            self.waits = 0

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.kills += 1

        def wait(self, timeout: float | None) -> int:
            del timeout
            self.waits += 1
            if self.waits == 1:
                raise process_module.subprocess.TimeoutExpired("command", 3)
            return -9

    process = StubbornProcess()

    def missing_group(_pid: int, _signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(process_module.os, "killpg", missing_group)
    process_module._terminate(  # noqa: SLF001 - exercise cleanup fallback contract.
        cast("subprocess.Popen[str]", process)
    )

    assert process.kills == 2
    assert process.waits == 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert process.stderr.closed


def test_termination_uses_direct_kill_off_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    class Process:
        pid = 424_244
        stdin = None
        stdout = None
        stderr = None

        def __init__(self) -> None:
            self.killed = False

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None) -> int:
            del timeout
            return -9

    process = Process()
    monkeypatch.setattr(process_module.os, "name", "nt")

    process_module._terminate(  # noqa: SLF001 - exercise portable cleanup contract.
        cast("subprocess.Popen[str]", process)
    )

    assert process.killed


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

        def communicate(self, _input: str | None, timeout: float | None) -> tuple[str, str]:
            del timeout
            raise KeyboardInterrupt

        def kill(self) -> None:
            self.returncode = -9

        def wait(self, timeout: float | None) -> int:
            del timeout
            self.waited = True
            return self.returncode

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
    assert signals == [(process.pid, process_module.signal.SIGKILL)]
    assert process.stdin.closed
    assert process.stdout.closed
    assert process.stderr.closed
