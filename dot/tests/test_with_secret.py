from __future__ import annotations

import errno
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fmind_dot import __version__
from fmind_dot.with_secret import main


def _setup_secret(
    tmp_path: Path, name: str = "TEST_API_KEY", content: bytes = b"synthetic-secret\n", mode: int = 0o600
) -> Path:
    secrets = tmp_path / ".config/dot/secrets"
    secrets.mkdir(parents=True, mode=0o700, exist_ok=True)
    secrets.chmod(0o700)
    path = secrets / name
    path.write_bytes(content)
    path.chmod(mode)
    return path


def test_with_secret_injects_file_and_env_without_argv_leak(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    monkeypatch.delenv("OTHER_API_KEY", raising=False)
    _setup_secret(tmp_path, "TEST_API_KEY", b"synthetic-0600\r\n", 0o600)
    _setup_secret(tmp_path, "READONLY_KEY", b"synthetic-0400\n", 0o400)
    calls: list[tuple[str, list[str], dict[str, str]]] = []

    def fake_exec(exe: str, argv: list[str], env: dict[str, str]) -> None:
        calls.append((exe, argv, env))

    main(["TEST_API_KEY", "--", sys.executable, "-c", "pass", "a b"], exec_fn=fake_exec)
    main(["READONLY_KEY", sys.executable, "-V"], exec_fn=fake_exec)

    assert len(calls) == 2
    assert calls[0][0] == shutil.which(sys.executable)
    assert calls[0][1] == [sys.executable, "-c", "pass", "a b"]
    assert all("synthetic-0600" not in arg for arg in calls[0][1])
    assert calls[0][2]["TEST_API_KEY"] == "synthetic-0600"
    assert calls[1][2]["READONLY_KEY"] == "synthetic-0400"

    monkeypatch.setenv("TEST_API_KEY", "synthetic-override")
    main(["TEST_API_KEY", "--", sys.executable, "-V"], exec_fn=fake_exec)
    assert calls[2][2]["TEST_API_KEY"] == "synthetic-override"

    monkeypatch.setattr(sys, "argv", ["with-secret", "TEST_API_KEY", sys.executable, "-V"])
    main(exec_fn=fake_exec)
    assert calls[3][2]["TEST_API_KEY"] == "synthetic-override"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], "usage:"),
        (["TEST_API_KEY"], "usage:"),
        (["bad-name", sys.executable], "uppercase environment variable name"),
        (["UV_PUBLISH_TOKEN", sys.executable], "Trusted Publishing"),
        (["TEST_API_KEY", "--"], "missing COMMAND"),
    ],
)
def test_with_secret_usage_errors(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 2
    assert expected in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["-h"], "usage: with-secret [-h] [-V] NAME [--] COMMAND [ARGS...]"),
        (["--help"], "usage: with-secret [-h] [-V] NAME [--] COMMAND [ARGS...]"),
        (["-V"], f"with-secret version {__version__}"),
        (["--version"], f"with-secret version {__version__}"),
    ],
)
def test_with_secret_help_and_version(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 0
    captured = capsys.readouterr()
    assert expected in captured.out
    if argv[0] in {"-h", "--help"}:
        assert "Exit codes:" in captured.out
        assert "Examples:" in captured.out
    assert captured.err == ""


def test_with_secret_forwards_help_flag_after_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    _setup_secret(tmp_path, "TEST_API_KEY", b"synthetic-help\n", 0o600)
    calls: list[list[str]] = []
    main(["TEST_API_KEY", "--", sys.executable, "--help"], exec_fn=lambda _exe, argv, _env: calls.append(argv))
    assert calls == [[sys.executable, "--help"]]


def test_with_secret_failures_and_security_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("TEST_API_KEY", raising=False)

    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", "--", "nonexistent-with-secret-command"])
    assert stopped.value.code == 1
    assert "required tools are missing" in capsys.readouterr().err

    for env_val in ("", "bad\nline"):
        monkeypatch.setenv("TEST_API_KEY", env_val)
        _setup_secret(tmp_path, "TEST_API_KEY", b"synthetic-personal\n", 0o600)
        with pytest.raises(SystemExit) as stopped:
            main(["TEST_API_KEY", "--", sys.executable, "-V"])
        assert stopped.value.code == 1
        err = capsys.readouterr().err
        assert "no personal fallback" in err
        assert "synthetic-personal" not in err
    monkeypatch.delenv("TEST_API_KEY", raising=False)

    secret = tmp_path / ".config/dot/secrets/TEST_API_KEY"
    secret.unlink()
    secrets_dir = secret.parent
    secrets_dir.rmdir()
    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "cannot read personal secret" in capsys.readouterr().err

    real_dir = tmp_path / "real_secrets"
    real_dir.mkdir(mode=0o700)
    secrets_dir.symlink_to(real_dir)
    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "chmod 700" in capsys.readouterr().err
    secrets_dir.unlink()

    secrets_dir.mkdir(mode=0o700)
    secrets_dir.chmod(0o755)
    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "chmod 700" in capsys.readouterr().err
    secrets_dir.chmod(0o700)

    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "cannot read personal secret" in capsys.readouterr().err

    target = tmp_path / "other"
    target.write_text("leak\n")
    secret.symlink_to(target)
    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "chmod 600" in capsys.readouterr().err
    secret.unlink()

    cases: list[tuple[bytes, int, str]] = [
        (b"ok\n", 0o644, "chmod 600"),
        (b"a" * 65_537, 0o600, "exceeds 64 KiB"),
        (b"a\x00b", 0o600, "NUL byte"),
        (b"\xff\xfe", 0o600, "UTF-8"),
        (b"\n", 0o600, "empty or contains a line break"),
        (b"a\nb\n", 0o600, "empty or contains a line break"),
    ]
    for payload, mode, msg in cases:
        _setup_secret(tmp_path, "TEST_API_KEY", payload, mode)
        with pytest.raises(SystemExit) as stopped:
            main(["TEST_API_KEY", sys.executable])
        assert stopped.value.code == 1
        assert msg in capsys.readouterr().err

    _setup_secret(tmp_path, "TEST_API_KEY", b"synthetic-valid\n", 0o600)

    def broken_exec(_exe: str, _argv: list[str], _env: dict[str, str]) -> None:
        raise OSError(errno.EACCES, "Permission denied")

    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable], exec_fn=broken_exec)
    assert stopped.value.code == 1
    assert "failed to execute" in capsys.readouterr().err

    secret.unlink()
    secret.mkdir(mode=0o700)
    with pytest.raises(SystemExit) as stopped:
        main(["TEST_API_KEY", sys.executable])
    assert stopped.value.code == 1
    assert "chmod 600" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_with_secret_closed_stdout_pipe_exits_141_without_stderr_noise(
    flag: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; from fmind_dot.with_secret import main; main(sys.argv[1:])", flag],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    proc.stdout.close()
    _out, err = proc.communicate(timeout=5)
    assert proc.returncode == 141
    assert err == b""

    monkeypatch.setattr(sys.stdout, "write", lambda _s: (_ for _ in ()).throw(BrokenPipeError()))
    with pytest.raises(SystemExit) as stopped:
        main([flag])
    assert stopped.value.code == 141

    class NoFilenoPipe:
        def write(self, _text: str) -> int:
            raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", NoFilenoPipe())
    with pytest.raises(SystemExit) as stopped_attr:
        main([flag])
    assert stopped_attr.value.code == 141
