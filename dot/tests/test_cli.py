from __future__ import annotations

import inspect
import os
import re
import sqlite3
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml
from typer import _click
from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

import fmind_dot.cli as cli
from fmind_dot.cli import app
from fmind_dot.errors import DotError
from fmind_dot.process import Runner

runner = CliRunner()
ROOT = Path(__file__).parents[2]


def test_root_help_exposes_python_first_command_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "agent (a)",
        "chezmoi (m)",
        "commit (c)",
        "completion (g)",
        "config (f)",
        "context (t)",
        "help (h)",
        "login (l)",
        "notify (n)",
        "prune (x)",
        "pull (p)",
        "pull-request (pr, b)",
        "release (r)",
        "setup (u)",
        "status (s)",
        "verify (v)",
        "version (i)",
    ):
        assert command in result.stdout


def test_subcommand_help_displays_nested_aliases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["config", "--help"])

    assert result.exit_code == 0
    for command in ("edit (e)", "init (i)", "path (p)", "show (s)", "validate (v)"):
        assert command in result.stdout


def test_root_command_tree_preserves_inventory_order_and_aliases() -> None:
    command = get_command(app)
    assert isinstance(command, TyperGroup)
    expected_aliases = {
        "agent": {"a"},
        "chezmoi": {"m"},
        "commit": {"c"},
        "completion": {"g"},
        "config": {"f"},
        "context": {"t"},
        "help": {"h"},
        "login": {"l"},
        "notify": {"n"},
        "prune": {"x"},
        "pull": {"p"},
        "pull-request": {"b", "pr"},
        "release": {"r"},
        "setup": {"u"},
        "status": {"s"},
        "verify": {"v"},
        "version": {"i"},
    }
    visible = [name for name in command.list_commands(_click.Context(command)) if not command.commands[name].hidden]

    assert visible == sorted(expected_aliases)
    assert set(command.commands) == set(expected_aliases) | {
        alias for aliases in expected_aliases.values() for alias in aliases
    }
    for name, aliases in expected_aliases.items():
        canonical = command.commands[name]
        for alias in aliases:
            aliased = command.commands[alias]
            assert aliased.hidden
            if isinstance(canonical, TyperGroup):
                assert isinstance(aliased, TyperGroup)
                assert {child_name for child_name, child in canonical.commands.items() if not child.hidden} == {
                    child_name for child_name, child in aliased.commands.items() if not child.hidden
                }
            else:
                assert aliased.callback is not None
                assert canonical.callback is not None
                assert inspect.unwrap(aliased.callback) is inspect.unwrap(canonical.callback)


def test_dot_cli_skill_documents_every_visible_top_level_command() -> None:
    command = get_command(app)
    assert isinstance(command, TyperGroup)
    visible = {name for name, child in command.commands.items() if not child.hidden}
    content = (ROOT / "skills/dot-cli/SKILL.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `dot ([a-z-]+)`", content, flags=re.MULTILINE))

    assert documented == visible
    assert "then rerun with `--apply`" not in content


def test_every_command_has_a_unique_one_letter_sibling_alias() -> None:
    def command_key(command: _click.Command) -> tuple[str, object]:
        if isinstance(command, TyperGroup):
            visible = tuple(name for name, child in command.commands.items() if not child.hidden)
            return "group", visible
        assert command.callback is not None
        return "command", inspect.unwrap(command.callback)

    def check_group(group: TyperGroup) -> None:
        aliases = {name: child for name, child in group.commands.items() if child.hidden and len(name) == 1}
        for name, child in group.commands.items():
            if child.hidden:
                continue
            matches = [alias for alias, candidate in aliases.items() if command_key(candidate) == command_key(child)]
            assert len(matches) == 1, f"command {name!r} has one-letter aliases {matches}"
            if isinstance(child, TyperGroup):
                check_group(child)

    command = get_command(app)
    assert isinstance(command, TyperGroup)
    check_group(command)


@pytest.mark.parametrize("arguments", [[], ["help"], ["h"]])
def test_root_help_command_and_bare_invocation_exit_successfully(
    arguments: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, arguments)

    assert result.exit_code == 0
    assert "Usage: dot [OPTIONS] COMMAND [ARGS]..." in result.stdout


def test_help_command_resolves_nested_command_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["help", "agent", "session"])

    assert result.exit_code == 0
    assert "Usage: dot agent session [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "Manage agent session logs" in result.stdout


@pytest.mark.parametrize("arguments", [["version"], ["i"], ["--version"], ["-v"]])
def test_version_matches_distribution(arguments: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, arguments)
    manifest = tomllib.loads((ROOT / "dot/pyproject.toml").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.stdout == f"dot version {manifest['project']['version']}\n"


def test_canonical_deep_prune_command_parses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["prune", "--all", "--deep", "--dry-run"])

    assert result.exit_code == 0
    assert "Prune (dry run)" in result.stdout
    assert "docker: would prune" in result.stdout


def test_explicit_missing_config_fails_before_non_config_command(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["--config", str(missing), "version"])

    assert result.exit_code == 1
    assert isinstance(result.exception, FileNotFoundError)
    assert "failed to read config file" in str(result.exception)
    assert "dot version" not in result.stdout


def test_main_reports_malformed_explicit_yaml_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("prune: [\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(malformed), "version"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.out == ""
    assert f"dot: failed to parse config file at {malformed}:" in captured.err
    assert "Traceback" not in captured.err


def test_config_repair_commands_accept_an_explicit_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["--config", str(missing), "config", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(missing)


def test_config_show_prints_the_effective_round_trippable_yaml(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("pull:\n  concurrency: 3\n", encoding="utf-8")

    result = runner.invoke(app, ["--config", str(path), "f", "s"])

    assert result.exit_code == 0
    rendered = yaml.safe_load(result.stdout)
    assert rendered["pull"]["concurrency"] == 3
    assert rendered["pull"]["directories"] == ["~/fmind", "~/fmind-ai", "~/mlops-courses"]
    assert rendered["verify"]["probe_concurrency"] == 8


def test_config_path_expands_the_current_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["--config", "~/custom/dot.yaml", "config", "path"])

    assert result.exit_code == 0
    assert result.stdout == f"{tmp_path}/custom/dot.yaml\n"


def test_config_init_round_trips_refuses_clobber_and_supports_force(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dot.yaml"

    initialized = runner.invoke(app, ["--config", str(path), "config", "init"])
    assert initialized.exit_code == 0
    assert initialized.stdout == f"✓ Wrote default configuration to {path}\n"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["pull"]["concurrency"] == 8

    path.write_text("pull:\n  concurrency: 2\n", encoding="utf-8")
    refused = runner.invoke(app, ["--config", str(path), "f", "i"])
    assert refused.exit_code == 1
    assert isinstance(refused.exception, DotError)
    assert "use --force to overwrite" in str(refused.exception)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["pull"]["concurrency"] == 2

    forced = runner.invoke(app, ["--config", str(path), "f", "i", "--force"])
    assert forced.exit_code == 0
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["pull"]["concurrency"] == 8


def test_config_init_rejects_a_dangling_symlink(tmp_path: Path) -> None:
    target = tmp_path / "missing.yaml"
    path = tmp_path / "dot.yaml"
    path.symlink_to(target)

    result = runner.invoke(app, ["--config", str(path), "config", "init"])

    assert result.exit_code == 1
    assert isinstance(result.exception, DotError)
    assert not target.exists()


def test_config_init_wraps_directory_creation_and_write_failures(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    nested = blocked_parent / "dot.yaml"

    directory_failure = runner.invoke(app, ["--config", str(nested), "config", "init"])
    assert directory_failure.exit_code == 1
    assert isinstance(directory_failure.exception, DotError)
    assert "failed to create config directory" in str(directory_failure.exception)

    directory_target = tmp_path / "directory.yaml"
    directory_target.mkdir()
    write_failure = runner.invoke(app, ["--config", str(directory_target), "config", "init", "--force"])
    assert write_failure.exit_code == 1
    assert isinstance(write_failure.exception, DotError)
    assert "failed to write config file" in str(write_failure.exception)


@pytest.mark.parametrize(
    ("editor", "expected"),
    [("custom-editor --wait", ["custom-editor", "--wait"]), ("   ", ["vi"])],
)
def test_config_edit_scaffolds_and_opens_the_selected_editor(
    editor: str,
    expected: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "dot.yaml"
    calls: list[list[str]] = []

    def found(_self: Runner, command: str) -> Path:
        return Path("/tools") / command

    def interactive(_self: Runner, arguments: Sequence[str], **_kwargs: object) -> int:
        calls.append(list(arguments))
        return 0

    monkeypatch.setenv("EDITOR", editor)
    monkeypatch.setattr(Runner, "which", found)
    monkeypatch.setattr(Runner, "interactive", interactive)

    result = runner.invoke(app, ["--config", str(path), "config", "edit"])

    assert result.exit_code == 0
    assert path.is_file()
    assert calls == [[*expected, str(path)]]


def test_config_edit_reports_missing_editor_and_failed_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("", encoding="utf-8")

    def missing(_self: Runner, _command: str) -> None:
        return None

    monkeypatch.setenv("EDITOR", "missing-editor")
    monkeypatch.setattr(Runner, "which", missing)
    unavailable = runner.invoke(app, ["--config", str(path), "config", "edit"])
    assert unavailable.exit_code == 1
    assert isinstance(unavailable.exception, DotError)
    assert str(unavailable.exception) == "editor 'missing-editor' not found in PATH"

    def found(_self: Runner, command: str) -> Path:
        return Path("/tools") / command

    def failed(_self: Runner, _arguments: Sequence[str], **_kwargs: object) -> int:
        return 23

    monkeypatch.setattr(Runner, "which", found)
    monkeypatch.setattr(Runner, "interactive", failed)
    failed_result = runner.invoke(app, ["--config", str(path), "config", "edit"])
    assert failed_result.exit_code == 1
    assert isinstance(failed_result.exception, DotError)
    assert str(failed_result.exception) == "editor exited with status 23"


def test_config_validate_distinguishes_defaults_explicit_missing_and_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    implicit = runner.invoke(app, ["config", "validate"])
    assert implicit.exit_code == 0
    assert "built-in defaults are in effect" in implicit.stdout

    missing = tmp_path / "missing.yaml"
    explicit = runner.invoke(app, ["--config", str(missing), "f", "v"])
    assert explicit.exit_code == 1
    assert isinstance(explicit.exception, FileNotFoundError)

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("pull:\n  directoories: []\n", encoding="utf-8")
    rejected = runner.invoke(app, ["--config", str(invalid), "config", "validate"])
    assert rejected.exit_code == 1
    assert "directoories" in str(rejected.exception)

    valid = tmp_path / "valid.yaml"
    valid.write_text("pull:\n  concurrency: 2\n", encoding="utf-8")
    accepted = runner.invoke(app, ["--config", str(valid), "config", "validate"])
    assert accepted.exit_code == 0
    assert accepted.stdout == f"✓ Configuration at {valid} is valid.\n"


@pytest.mark.parametrize(
    "error",
    [
        DotError("broken command"),
        PermissionError("permission denied"),
        sqlite3.OperationalError("database is locked"),
        ValueError("invalid input"),
    ],
    ids=["dot-error", "os-error", "sqlite-error", "invalid-value"],
)
def test_main_reports_expected_errors_without_a_traceback(
    error: Exception, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail() -> None:
        raise error

    monkeypatch.setattr(cli, "_invoke_app", fail)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.out == ""
    assert captured.err == f"dot: {error}\n"


def test_python_module_entrypoint_reports_config_os_failure_without_traceback(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fmind_dot",
            "--config",
            str(blocked_parent / "dot.yaml"),
            "config",
            "init",
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("dot: failed to create config directory:")
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("arguments", "expected_exit", "expected_error"),
    [
        (["--unknown-option"], 1, "No such option: --unknown-option"),
        (["unknown-command"], 3, "No such command 'unknown-command'"),
        (["help", "unknown-command"], 3, "No help topic for 'unknown-command'"),
    ],
)
def test_python_module_entrypoint_preserves_parser_exit_codes(
    arguments: list[str], expected_exit: int, expected_error: str, tmp_path: Path
) -> None:
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "fmind_dot", *arguments],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == expected_exit
    assert result.stdout == ""
    assert expected_error in result.stderr
    assert "Traceback" not in result.stderr


def test_main_maps_keyboard_interrupt_to_shell_exit_130(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_invoke_app", interrupt)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 130
    assert captured.out == ""
    assert captured.err == ""


def test_main_does_not_hide_programmer_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise RuntimeError("programmer error")

    monkeypatch.setattr(cli, "_invoke_app", fail)

    with pytest.raises(RuntimeError, match="programmer error"):
        cli.main()
