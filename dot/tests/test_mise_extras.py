"""Exercise optional tool selection through real chezmoi and mise boundaries."""

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTRAS = ("airflow", "atlassian", "aws", "databricks", "kubernetes")


@pytest.fixture
def workstation(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    source = tmp_path / "source"
    home = tmp_path / "destination"
    home.mkdir()
    shutil.copytree(ROOT / "dot_config/mise/conf.d", source / "dot_config/mise/conf.d")
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates")
    shutil.copyfile(ROOT / ".chezmoiignore", source / ".chezmoiignore")
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    command = [
        "chezmoi",
        "--source",
        str(source),
        "--destination",
        str(home),
        "--config",
        str(config),
        "--cache",
        str(tmp_path / "cache"),
        "--persistent-state",
        str(tmp_path / "state.boltdb"),
        "apply",
        "--force",
    ]
    return home, config, command


def apply(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)


@pytest.mark.parametrize("extra", EXTRAS)
def test_extra_enable_disable_preserves_host_fragments(
    workstation: tuple[Path, Path, list[str]],
    extra: str,
) -> None:
    home, config, command = workstation
    directory = home / ".config/mise/conf.d"
    directory.mkdir(parents=True)
    personal = directory / "personal.toml"
    personal.write_text('[env]\nPERSONAL = "kept"\n')
    assert apply(command).returncode == 0
    assert list(directory.iterdir()) == [personal]
    config.write_text(f'[data]\nextras = ["{extra}"]\n')
    result = apply(command)
    assert result.returncode == 0, result.stderr
    fragment = directory / f"{extra}.local.toml"
    enabled = fragment.read_text()
    assert tomllib.loads(enabled)["tools"]
    assert apply(command).returncode == 0
    assert fragment.read_text() == enabled
    assert sorted(p.name for p in directory.iterdir()) == sorted([fragment.name, personal.name])
    config.write_text("[data]\nextras = []\n")
    result = apply(command)
    assert result.returncode == 0, result.stderr
    assert not fragment.exists()
    assert personal.read_text() == '[env]\nPERSONAL = "kept"\n'


@pytest.mark.parametrize("value", ['"aws"', '["awss"]', "[1]", "{}", "false"])
def test_invalid_extras_fail_before_changing_files(
    workstation: tuple[Path, Path, list[str]],
    value: str,
) -> None:
    home, config, command = workstation
    config.write_text('[data]\nextras = ["aws"]\n')
    assert apply(command).returncode == 0
    fragment = home / ".config/mise/conf.d/aws.local.toml"
    before = fragment.read_bytes()
    config.write_text(f"[data]\nextras = {value}\n")
    result = apply(command)
    assert result.returncode != 0
    assert "extra" in result.stderr
    assert fragment.read_bytes() == before


def test_mise_discovers_all_rendered_extras(workstation: tuple[Path, Path, list[str]]) -> None:
    home, config, command = workstation
    config.write_text(f"[data]\nextras = {json.dumps(EXTRAS)}\n")
    result = apply(command)
    assert result.returncode == 0, result.stderr
    mise_dir = home / ".config/mise"
    (mise_dir / "config.toml").write_text("[tools]\n")
    environment = dict(os.environ, MISE_CONFIG_DIR=str(mise_dir), MISE_TRUSTED_CONFIG_PATHS=str(mise_dir))
    for key in ("MISE_GLOBAL_CONFIG_FILE", "MISE_CONFIG_FILE", "MISE_ENV"):
        environment.pop(key, None)
    result = subprocess.run(
        ["mise", "-C", str(home), "config", "ls", "--json"],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert not result.stderr
    configs = json.loads(result.stdout)
    paths = {entry["path"] for entry in configs}
    assert {str(mise_dir / "conf.d" / f"{extra}.local.toml") for extra in EXTRAS} <= paths
