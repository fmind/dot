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
        check: bool,
        timeout: int,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert timeout > 0
        commands.append(args)
        assert cwd is not None
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
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", run)
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
        check: bool,
        timeout: int,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert timeout > 0
        assert cwd is not None
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
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", run)
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
        check: bool,
        timeout: int,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check
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
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", run)
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

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("invalid input must not reach mise")

    monkeypatch.setattr(subprocess, "run", run)
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
        check: bool,
        timeout: int,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert timeout > 0
        seen.append((cwd, env["MISE_TRUSTED_CONFIG_PATHS"]))
        write_bundle(Path(env["MISE_CONFIG_DIR"]), b"resolved graph\n")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(mise_refresh.tempfile, "TemporaryDirectory", FakeTempDir)
    monkeypatch.setattr(subprocess, "run", fake_run)
    mise_refresh.refresh(tmp_path)

    resolved = real_tmp.resolve()
    assert seen == [(resolved, str(resolved))]
