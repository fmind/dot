from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from dot_tasks import mise_refresh
from dot_tasks.mise_locks import bundle

CONFIG = """[settings]
lockfile_platforms = ["linux-x64", "macos-arm64"]
[tools]
"pypi:example" = "latest"
native = "latest"
linux_only = {version = "latest", os = ["linux"]}
"""


def write_bundle(directory: Path, content: bytes = b"old graph\n") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.toml").write_text(CONFIG)
    graph = directory / "locks/example/1.0"
    graph.mkdir(parents=True, exist_ok=True)
    (graph / "uv.lock").write_bytes(content)
    (graph / "pyproject.toml").write_text("[project]\nname='example'\n")
    (directory / "mise.lock").write_text(
        'lockfile_version = 4\n[[tools."pypi:example"]]\nversion = "1.0"\n'
        f'uv = {{path = "locks/example/1.0", digest = "sha256:{hashlib.sha256(content).hexdigest()}"}}\n'
        '[[tools.native]]\nversion = "2.0"\n'
        '[tools.native."platforms.linux-x64"]\nurl = "https://example.org/linux"\nchecksum = "sha256:linux"\n'
        '[tools.native."platforms.macos-arm64"]\nurl = "https://example.org/macos"\nchecksum = "sha256:macos"\n'
        '[[tools.linux_only]]\nversion = "1.0"\n'
        '[tools.linux_only."platforms.linux-x64"]\nurl = "https://example.org/linux-only"\nchecksum = "sha256:linux-only"\n'
    )


@pytest.mark.parametrize(
    ("bump", "tools", "expected"),
    [
        (False, (), []),
        (True, (), ["--bump"]),
        # An unbumped lock would resolve "latest" to the installed version.
        (False, ("pypi:example",), ["--bump", "pypi:example"]),
        (False, ("pypi:example", "native"), ["--bump", "pypi:example", "native"]),
    ],
)
@pytest.mark.parametrize("old_damage", ["none", "missing", "digest"])
def test_refresh_uses_portable_source_and_isolated_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    bump: bool,
    tools: tuple[str, ...],
    expected: list[str],
    old_damage: str,
) -> None:
    root = tmp_path / "repository"
    source = root / "dot_config/mise"
    write_bundle(source)
    graph = source / "locks/example/1.0/uv.lock"
    if old_damage == "missing":
        graph.unlink()
    elif old_damage == "digest":
        graph.write_bytes(b"damaged graph\n")
    live_config = tmp_path / "live/config.toml"
    live_config.parent.mkdir()
    live_config.write_text('"pypi:example"="path:/private/runtime"\n')
    system_config = tmp_path / "system/config.toml"
    system_config.parent.mkdir()
    system_config.write_text('[tools]\n"pypi:machine-only"="1.0"\n')
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(live_config))
    monkeypatch.setenv("MISE_CONFIG_DIR", str(live_config.parent))
    monkeypatch.setenv("MISE_SYSTEM_CONFIG_FILE", str(system_config))
    monkeypatch.setenv("MISE_SYSTEM_CONFIG_DIR", str(system_config.parent))
    commands: list[list[str]] = []
    staging: list[Path] = []
    real_run = subprocess.run

    def run(
        args: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: Path,
    ) -> None:
        assert timeout > 0
        commands.append(args)
        assert cwd != root
        staging.append(cwd)
        configuration = Path(env["MISE_CONFIG_DIR"])
        assert configuration == cwd / ".config/mise"
        assert env["MISE_GLOBAL_CONFIG_FILE"] == str(configuration / "config.toml")
        assert env["MISE_STATE_DIR"] == str(cwd / "state-mise")
        # Locked mode would refuse a newly declared tool; only this writer lifts it.
        assert env["MISE_LOCKED"] == "0"
        assert (configuration / "config.toml").read_text() == CONFIG
        assert (configuration / "mise.lock").read_bytes() == (source / "mise.lock").read_bytes()
        # Resolve real mise configuration without invoking the lock writer or installers.
        discovered = real_run(
            ["mise", "config", "ls", "--json"],
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # mise resolves symlinks, including /var -> /private/var on macOS.
        assert [Path(entry["path"]).resolve() for entry in json.loads(discovered.stdout)] == [
            (configuration / "config.toml").resolve()
        ]
        write_bundle(configuration, b"refreshed graph\n")

    monkeypatch.setattr(mise_refresh, "_run_lock", run)
    mise_refresh.refresh(root, bump=bump, tools=tools)

    assert commands[-1] == ["mise", "lock", "--global", "--yes", *expected]
    assert graph.read_bytes() == b"refreshed graph\n"
    assert live_config.read_text() == '"pypi:example"="path:/private/runtime"\n'
    assert all(not path.exists() for path in staging)
    bundle(source / "mise.lock")


@pytest.mark.parametrize("failure", ["command", "missing_tool", "missing_platform", "missing_graph", "digest"])
def test_refresh_failure_preserves_the_managed_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    source = tmp_path / "dot_config/mise"
    write_bundle(source)
    before = bundle(source / "mise.lock")
    staging: list[Path] = []

    def run(
        args: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: Path,
    ) -> None:
        assert timeout > 0
        staging.append(cwd)
        configuration = Path(env["MISE_CONFIG_DIR"])
        write_bundle(configuration, b"new graph\n")
        lock = configuration / "mise.lock"
        if failure == "command":
            raise subprocess.CalledProcessError(1, args)
        if failure == "missing_tool":
            lock.write_text(lock.read_text().replace('tools."pypi:example"', 'tools."pypi:other"'))
        elif failure == "missing_platform":
            lock.write_text(lock.read_text().replace("platforms.macos-arm64", "platforms.macos-x64"))
        elif failure == "missing_graph":
            lock.write_text("\n".join(line for line in lock.read_text().splitlines() if not line.startswith("uv =")))
        else:
            (configuration / "locks/example/1.0/uv.lock").write_bytes(b"corrupt\n")

    monkeypatch.setattr(mise_refresh, "_run_lock", run)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        mise_refresh.refresh(tmp_path)
    assert bundle(source / "mise.lock") == before
    assert all(not path.exists() for path in staging)


def test_validate_reports_every_unverifiable_platform_artifact(tmp_path: Path) -> None:
    write_bundle(tmp_path)
    lock = tmp_path / "mise.lock"
    lock.write_text(lock.read_text().replace('checksum = "sha256:macos"\n', ""))
    with pytest.raises(ValueError, match="native macos-arm64: checksum missing"):
        mise_refresh.validate(tmp_path)


def test_validate_requires_pypi_tools_to_bind_to_global_python(tmp_path: Path) -> None:
    write_bundle(tmp_path)
    config = tmp_path / "config.toml"
    lock = tmp_path / "mise.lock"
    config.write_text(config.read_text() + 'python = "3.14"\n')
    lock.write_text(
        lock.read_text()
        + '[[tools.python]]\nversion = "3.14.10"\n'
        + '[tools.python."platforms.linux-x64"]\nurl = "https://example.org/py-linux"\nchecksum = "sha256:py-linux"\n'
        + '[tools.python."platforms.macos-arm64"]\nurl = "https://example.org/py-macos"\nchecksum = "sha256:py-macos"\n'
    )
    with pytest.raises(ValueError, match=r"pypi:example: missing python = '3\.14'"):
        mise_refresh.validate(tmp_path)

    config.write_text(
        config.read_text().replace(
            '"pypi:example" = "latest"', '"pypi:example" = {version = "latest", python = "3.14"}'
        )
    )
    with pytest.raises(ValueError, match=r"pypi:example: lock options missing python = '3\.14'"):
        mise_refresh.validate(tmp_path)

    lock.write_text(
        lock.read_text().replace(
            '[[tools."pypi:example"]]\nversion = "1.0"\n',
            '[[tools."pypi:example"]]\nversion = "1.0"\noptions = {python = "3.14"}\n',
        )
    )
    mise_refresh.validate(tmp_path)


def test_refresh_tool_moves_only_its_entry_and_retires_the_old_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "dot_config/mise"
    write_bundle(source)
    untouched = (source / "mise.lock").read_text().split("[[tools.native]]")[1]

    def run(
        args: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: Path,
    ) -> None:
        assert timeout > 0
        assert cwd is not None
        assert args[-2:] == ["--bump", "pypi:example"]
        # Simulate mise bumping one tool: its entry and graph folder move to 2.0, the rest stays.
        configuration = Path(env["MISE_CONFIG_DIR"])
        old = configuration / "locks/example/1.0"
        new = old.parent / "2.0"
        old.rename(new)
        content = (new / "uv.lock").read_bytes()
        lock = configuration / "mise.lock"
        lock.write_text(lock.read_text().replace('"1.0"\nuv', '"2.0"\nuv', 1).replace("example/1.0", "example/2.0"))
        assert hashlib.sha256(content).hexdigest() in lock.read_text()

    monkeypatch.setattr(mise_refresh, "_run_lock", run)
    mise_refresh.refresh(tmp_path, tools=["pypi:example"])

    lock = (source / "mise.lock").read_text()
    assert 'version = "2.0"\nuv = {path = "locks/example/2.0"' in lock
    assert lock.split("[[tools.native]]")[1] == untouched
    assert not (source / "locks/example/1.0").exists()
    bundle(source / "mise.lock")


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--bump", "--tool", "native"], "not allowed with argument"),
        (["--tool", "pypi:missing"], "undeclared tools pypi:missing"),
        (["--tool", "pypi:example@2.0"], "undeclared tools pypi:example@2.0"),
    ],
)
def test_main_rejects_invalid_selections_before_resolving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    message: str,
) -> None:
    source = tmp_path / "dot_config/mise"
    write_bundle(source)
    before = bundle(source / "mise.lock")

    def run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalid input must not reach mise")

    monkeypatch.setattr(mise_refresh, "_run_lock", run)
    monkeypatch.setattr(mise_refresh, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["mise_refresh", *arguments])
    with pytest.raises(SystemExit) as exit_info:
        mise_refresh.main()
    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err
    assert bundle(source / "mise.lock") == before


@pytest.mark.parametrize(
    ("bump", "tools", "message"),
    [(True, ["native"], "either bump"), (False, ["pypi:missing"], "declare the tool")],
)
def test_refresh_rejects_invalid_selections(tmp_path: Path, *, bump: bool, tools: list[str], message: str) -> None:
    write_bundle(tmp_path / "dot_config/mise")
    with pytest.raises(ValueError, match=message):
        mise_refresh.refresh(tmp_path, bump=bump, tools=tools)


def test_refresh_resolves_symlinked_tempdir_for_mise_trust(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "dot_config/mise"
    write_bundle(source)
    real_tmp = tmp_path / "real-tmp"
    real_tmp.mkdir()
    link_tmp = tmp_path / "link-tmp"
    link_tmp.symlink_to(real_tmp)
    seen: list[tuple[Path | None, str]] = []

    class FakeTempDir:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> str:
            return str(link_tmp)

        def __exit__(self, *_args: object) -> None:
            pass

    def fake_run(
        args: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: Path,
    ) -> None:
        assert timeout > 0
        seen.append((cwd, env["MISE_TRUSTED_CONFIG_PATHS"]))
        write_bundle(Path(env["MISE_CONFIG_DIR"]), b"resolved graph\n")
        del args

    monkeypatch.setattr(mise_refresh.tempfile, "TemporaryDirectory", FakeTempDir)
    monkeypatch.setattr(mise_refresh, "_run_lock", fake_run)
    mise_refresh.refresh(tmp_path)

    resolved = real_tmp.resolve()
    assert seen == [(resolved, str(resolved))]


def test_run_lock_kills_process_group_on_timeout_and_raises_on_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import signal
    import threading
    import time

    from fmind_dot import process as process_module

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        mise_refresh._run_lock([sys.executable, "-c", "raise SystemExit(4)"], cwd=tmp_path, env=dict(os.environ))  # noqa: SLF001
    assert exc_info.value.returncode == 4

    monkeypatch.setattr(process_module, "_TERMINATION_GRACE_SECONDS", 0.2)
    with pytest.raises(subprocess.TimeoutExpired):
        mise_refresh._run_lock(  # noqa: SLF001
            [sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path, env=dict(os.environ), timeout=0.15
        )

    # Leader uses default SIGTERM (exits immediately) while grandchild installs SIG_IGN and atomically publishes its PID.
    # Waiting for readiness avoids fixed startup races and verifies terminate_process still SIGKILLs surviving PGID members.
    child_pid_file = tmp_path / "child.pid"
    grandchild_code = (
        "import os, pathlib, signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"dst = pathlib.Path({str(child_pid_file)!r})\n"
        "tmp = dst.with_suffix('.tmp')\n"
        "tmp.write_text(str(os.getpid()), encoding='utf-8')\n"
        "os.replace(tmp, dst)\n"
        "time.sleep(60)\n"
    )
    parent_code = (
        f"import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', {grandchild_code!r}])\ntime.sleep(60)\n"
    )
    ready_timeout_hit = False

    def trigger_sigterm_when_ready() -> None:
        nonlocal ready_timeout_hit
        wait_until = time.monotonic() + 10.0
        while time.monotonic() < wait_until:
            if child_pid_file.is_file():
                signal.raise_signal(signal.SIGTERM)
                return
            time.sleep(0.02)
        ready_timeout_hit = True
        signal.raise_signal(signal.SIGTERM)

    watcher = threading.Thread(target=trigger_sigterm_when_ready, daemon=True)
    watcher.start()
    child_pid: int | None = None
    try:
        with pytest.raises(KeyboardInterrupt), process_module.sigterm_as_keyboard_interrupt():
            mise_refresh._run_lock(  # noqa: SLF001
                [sys.executable, "-c", parent_code], cwd=tmp_path, env=dict(os.environ), timeout=30.0
            )
        watcher.join(timeout=2.0)
        assert not ready_timeout_hit
        assert child_pid_file.is_file()
        child_pid = int(child_pid_file.read_text(encoding="utf-8").strip())
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        if child_pid is not None:
            from contextlib import suppress

            with suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)
