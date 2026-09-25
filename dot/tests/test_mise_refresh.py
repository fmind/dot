from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from dot_tasks import mise_refresh
from dot_tasks.mise_locks import bundle

CONFIG = """[settings]
lockfile_platforms = ["linux-x64", "macos-arm64"]
[tools]
"pipx:example" = "latest"
native = "latest"
linux_only = {version = "latest", os = ["linux"]}
"""


def write_bundle(directory: Path, content: bytes = b"old graph\n") -> None:
    graph = directory / "locks/example/1.0"
    graph.mkdir(parents=True, exist_ok=True)
    (graph / "uv.lock").write_bytes(content)
    (graph / "pyproject.toml").write_text("[project]\nname='example'\n")
    (directory / "mise.lock").write_text(
        'lockfile_version = 2\n[[tools."pipx:example"]]\nversion = "1.0"\n'
        f'uv = {{path = "locks/example/1.0", digest = "sha256:{hashlib.sha256(content).hexdigest()}"}}\n'
        '[[tools.native]]\nversion = "2.0"\n'
        '[tools.native."platforms.linux-x64"]\nurl = "https://example.org/linux"\n'
        '[tools.native."platforms.macos-arm64"]\nurl = "https://example.org/macos"\n'
        '[[tools.linux_only]]\nversion = "1.0"\n'
        '[tools.linux_only."platforms.linux-x64"]\nurl = "https://example.org/linux-only"\n'
    )


@pytest.mark.parametrize("bump", [False, True])
@pytest.mark.parametrize("old_damage", ["none", "missing", "digest"])
def test_refresh_uses_portable_source_and_isolated_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, bump: bool, old_damage: str
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
    live_config.write_text('"pipx:example"="path:/private/runtime"\n')
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(live_config))
    monkeypatch.setenv("MISE_CONFIG_DIR", str(live_config.parent))
    commands: list[list[str]] = []
    staging: list[Path] = []

    def run(
        args: list[str],
        *,
        env: dict[str, str],
        check: bool,
        timeout: int,
        cwd: Path | None = None,
        capture_output: bool = False,
        text: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert timeout > 0
        commands.append(args)
        if args[0] == "chezmoi":
            assert str(source / "config.toml.tmpl") in args
            assert capture_output
            assert text
            return subprocess.CompletedProcess(args, 0, CONFIG)
        assert cwd is not None
        assert cwd != root
        staging.append(cwd)
        configuration = Path(env["MISE_CONFIG_DIR"])
        assert configuration == cwd / ".config/mise"
        assert env["MISE_GLOBAL_CONFIG_FILE"] == str(configuration / "config.toml")
        assert (configuration / "config.toml").read_text() == CONFIG
        assert (configuration / "mise.lock").read_bytes() == (source / "mise.lock").read_bytes()
        write_bundle(configuration, b"refreshed graph\n")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", run)
    mise_refresh.refresh(root, bump=bump)

    assert commands[-1] == ["mise", "lock", "--global", "--yes", *(["--bump"] if bump else [])]
    assert graph.read_bytes() == b"refreshed graph\n"
    assert live_config.read_text() == '"pipx:example"="path:/private/runtime"\n'
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
        capture_output: bool = False,
        text: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert timeout > 0
        if args[0] == "chezmoi":
            assert capture_output
            assert text
            return subprocess.CompletedProcess(args, 0, CONFIG)
        assert cwd is not None
        staging.append(cwd)
        configuration = Path(env["MISE_CONFIG_DIR"])
        write_bundle(configuration, b"new graph\n")
        lock = configuration / "mise.lock"
        if failure == "command":
            raise subprocess.CalledProcessError(1, args)
        if failure == "missing_tool":
            lock.write_text(lock.read_text().replace('tools."pipx:example"', 'tools."pipx:other"'))
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
