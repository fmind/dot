from __future__ import annotations

import os
import re
import shlex
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
ROOT = Path(__file__).resolve().parents[2]


def test_root_help_exposes_python_first_command_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout
    for command in (
        "agent",
        "config",
        "doctor",
        "pull",
        "status",
    ):
        assert command in result.stdout
    # Repository tasks and release gates call `dot completion`; it stays out of everyday help.
    assert not re.search(r"^\s*completion\s", result.stdout, flags=re.MULTILINE)
    for removed in (
        "context",
        "help",
        "notify",
        "version",
        "commit",
        "pr",
        "release",
        "chezmoi",
        "verify",
    ):
        assert not re.search(rf"^\s*{removed}(?:\s|$)", result.stdout, flags=re.MULTILINE)


@pytest.mark.parametrize("option", ["--install-completion", "--show-completion"])
def test_duplicate_completion_options_are_rejected(option: str) -> None:
    result = runner.invoke(app, [option, "fish"])
    assert result.exit_code == 2
    assert "No such option" in result.output


@pytest.mark.parametrize(
    ("instruction", "expected"),
    [("source_fish", "complete --command dot"), ("complete_fish", "doctor")],
)
def test_fish_completion_protocol_works_in_fresh_process(instruction: str, expected: str, tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from fmind_dot.cli import app; app(prog_name='dot')"],
        cwd=tmp_path,
        env={
            **os.environ,
            "_DOT_COMPLETE": instruction,
            "_TYPER_COMPLETE_ARGS": "dot doc",
            "_TYPER_COMPLETE_FISH_ACTION": "get-args",
        },
        capture_output=True,
        text=True,
        # Returns as soon as the CLI exits; a fresh interpreter can take seconds under load.
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    assert result.stderr == ""


def test_subcommand_help_displays_canonical_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["config", "--help"])

    assert result.exit_code == 0
    for command in ("edit", "path", "show"):
        assert command in result.stdout
    assert not re.search(r"\([a-z]\)", result.stdout)


def test_root_command_tree_has_only_the_canonical_runtime_commands() -> None:
    command = get_command(app)
    assert isinstance(command, TyperGroup)
    expected = {
        "agent",
        "cache",
        "completion",
        "config",
        "doctor",
        "login",
        "orphan",
        "prune",
        "pull",
        "secret",
        "setup",
        "status",
        "trust",
    }
    visible = [name for name in command.list_commands(_click.Context(command)) if not command.commands[name].hidden]

    assert set(visible) == expected - {"completion"}
    assert set(command.commands) == expected


@pytest.mark.parametrize(
    ("path", "names"),
    [
        (
            [],
            [
                "agent",
                "cache",
                "config",
                "doctor",
                "login",
                "prune",
                "pull",
                "secret",
                "setup",
                "status",
                "trust",
            ],
        ),
        (["config"], ["edit", "path", "show"]),
        (["agent"], ["context", "doctor", "session", "stats"]),
        (["agent", "session"], ["list", "show", "sync"]),
        (["agent", "hook"], ["notify"]),
    ],
)
def test_help_lists_commands_alphabetically(
    path: list[str], names: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, [*path, "--help"])
    assert result.exit_code == 0
    rows = [match.group(1) for match in re.finditer(r"(?m)^[│ ]+(\S+)\s", _click.utils.strip_ansi(result.stdout))]
    assert [name for name in rows if name in names] == names


def test_agent_command_tree_keeps_hooks_internal_and_sync_as_the_only_capture() -> None:
    root = get_command(app)
    assert isinstance(root, TyperGroup)
    agent = root.commands["agent"]
    assert isinstance(agent, TyperGroup)
    assert {name for name, child in agent.commands.items() if not child.hidden} == {
        "context",
        "doctor",
        "session",
        "stats",
    }
    assert agent.commands["hook"].hidden
    hook = agent.commands["hook"]
    assert isinstance(hook, TyperGroup)
    assert set(hook.commands) == {"notify"}

    session = agent.commands["session"]
    assert isinstance(session, TyperGroup)
    assert set(session.commands) == {"list", "show", "sync"}


def documented_dot_examples() -> list[str]:
    """Collect `dot ...` lines from fenced examples in the README and every skill."""
    sources = [
        ROOT / "README.md",
        *sorted((ROOT / "skills").rglob("*.md")),
        *sorted((ROOT / ".agents/skills").rglob("*.md")),
    ]
    examples: list[str] = []
    for source in sources:
        fenced = False
        for line in source.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
            elif fenced and line.startswith("dot ") and " -- " not in line:
                examples.append(line.split("#", 1)[0].split("|", 1)[0].strip())
    return sorted(set(examples))


@pytest.mark.parametrize("example", documented_dot_examples())
def test_documented_dot_examples_parse(example: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # --help stops after parsing, so unknown commands and options fail without running anything.
    result = runner.invoke(app, [*shlex.split(example)[1:], "--help"])

    assert result.exit_code == 0, result.output


def test_bare_invocation_exits_successfully_with_help(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage: dot [OPTIONS] COMMAND [ARGS]..." in _click.utils.strip_ansi(result.stdout)


@pytest.mark.parametrize("arguments", [["--version"], ["-V"]])
def test_version_matches_distribution(arguments: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, arguments)
    manifest = tomllib.loads((ROOT / "dot/pyproject.toml").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert result.stdout == f"dot version {manifest['project']['version']}\n"


def test_explicit_missing_config_fails_before_non_config_command(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["--config", str(missing), "doctor"])

    assert result.exit_code == 1
    assert isinstance(result.exception, FileNotFoundError)
    assert "failed to read config file" in str(result.exception)
    assert result.stdout == ""


def test_main_reports_invalid_config_with_path_and_repair_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("pull:\n  concurrency: lots\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(invalid), "doctor"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert f"dot: invalid config file at {invalid} (1 validation error(s)): pull.concurrency:" in captured.err
    assert "fix it with: dot config edit" in captured.err
    assert "lots" not in captured.err


def test_main_reports_malformed_explicit_yaml_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("prune: [\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(malformed), "doctor"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.out == ""
    assert f"dot: failed to parse config file at {malformed}:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "content",
    [
        "api_token: SYNTHETIC_PRIVATE_VALUE\n",
        "pull:\n  timeout_seconds: SYNTHETIC_PRIVATE_VALUE\n",
        "auth: !SYNTHETIC_PRIVATE_VALUE {}\n",
    ],
)
def test_config_validation_errors_do_not_disclose_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(content)
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(config), "config", "show"])
    with pytest.raises(SystemExit) as stopped:
        cli.main()
    captured = capsys.readouterr()
    assert stopped.value.code == 1
    assert captured.out == ""
    assert "SYNTHETIC_PRIVATE_VALUE" not in captured.err
    assert "Traceback" not in captured.err
    assert "validation error" in captured.err or "invalid YAML at line 1, column 7" in captured.err


def test_config_repair_commands_accept_an_explicit_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["--config", str(missing), "config", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(missing)


def test_config_show_prints_the_effective_round_trippable_yaml(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("pull:\n  concurrency: 3\n", encoding="utf-8")

    result = runner.invoke(app, ["--config", str(path), "config", "show"])

    assert result.exit_code == 0
    rendered = yaml.safe_load(result.stdout)
    assert rendered["pull"]["concurrency"] == 3
    assert rendered["pull"]["directories"] == ["~/fmind", "~/fmind-ai", "~/mlops-courses"]
    assert rendered["doctor"]["probe_concurrency"] == 8


def test_config_path_expands_the_current_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["--config", "~/custom/dot.yaml", "config", "path"])

    assert result.exit_code == 0
    assert result.stdout == f"{tmp_path}/custom/dot.yaml\n"


@pytest.mark.parametrize(
    ("editor", "expected"),
    [("custom-editor --wait", ["custom-editor", "--wait"]), ("   ", ["vi"])],
)
def test_config_edit_opens_the_selected_editor_and_validates(
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
        Path(arguments[-1]).write_text("pull:\n  concurrency: 2\n", encoding="utf-8")
        return 0

    monkeypatch.setenv("EDITOR", editor)
    monkeypatch.setattr(Runner, "which", found)
    monkeypatch.setattr(Runner, "interactive", interactive)

    result = runner.invoke(app, ["--config", str(path), "config", "edit"])

    assert result.exit_code == 0
    assert calls == [[*expected, str(path)]]
    assert result.stdout == "✓ Configuration is valid.\n"


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
    # A PATH with only a stub editor keeps the child away from workstation tools.
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/editor").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "bin/editor").chmod(0o755)
    environment["PATH"] = str(tmp_path / "bin")
    environment["EDITOR"] = "editor"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fmind_dot",
            "--config",
            str(blocked_parent / "dot.yaml"),
            "config",
            "edit",
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("dot: failed to create config directory:")
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("arguments", "expected_exit", "expected_error"),
    [
        (["--unknown-option"], 2, "No such option: --unknown-option"),
        (["unknown-command"], 2, "No such command 'unknown-command'"),
        (["help", "unknown-command"], 2, "No such command 'help'"),
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
        timeout=30,
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
    assert captured.err == "Cancelled.\n"


def test_main_reports_keyboard_interrupt_raised_inside_a_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def interrupt(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli, "state_from", interrupt)
    monkeypatch.setattr(sys, "argv", ["dot", "config", "show"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 130
    assert captured.out == ""
    assert captured.err == "Cancelled.\n"


def test_main_does_not_hide_programmer_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise RuntimeError("programmer error")

    monkeypatch.setattr(cli, "_invoke_app", fail)

    with pytest.raises(RuntimeError, match="programmer error"):
        cli.main()


@pytest.mark.parametrize(
    "path",
    [
        [],
        ["config"],
        ["agent"],
        ["agent", "session"],
        ["login"],
        ["setup"],
        ["prune"],
    ],
)
def test_bare_groups_show_help_successfully_without_actions(
    path: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Runner, "which", lambda *_: pytest.fail("help must not inspect or run native tools"))
    result = runner.invoke(app, path)
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.stdout
    assert "Commands" in result.stdout


def test_every_command_and_group_has_a_description() -> None:
    def inspect(command: _click.Command, path: str) -> None:
        assert command.help, f"missing description: {path}"
        assert command.help.strip(), f"empty description: {path}"
        if isinstance(command, TyperGroup):
            for name, child in command.commands.items():
                inspect(child, f"{path} {name}")

    inspect(get_command(app), "dot")


def test_date_filters_share_values_and_name_their_time_basis() -> None:
    help_by_path: dict[str, str] = {}

    def inspect(command: _click.Command, path: str) -> None:
        for parameter in command.params:
            if parameter.opts[0] in {"--since", "--until"}:
                help_by_path[f"{path} {parameter.opts[0]}"] = getattr(parameter, "help", "") or ""
        if isinstance(command, TyperGroup):
            for name, child in command.commands.items():
                inspect(child, f"{path} {name}")

    inspect(get_command(app), "dot")
    assert help_by_path["dot agent session list --since"].startswith("Ingested since")
    assert help_by_path["dot agent stats --until"].startswith("Active until")
    assert help_by_path["dot agent session sync --since"].startswith("Only sources modified since")
    for path, text in help_by_path.items():
        values = "UTC date (whole day)" if path.endswith("--until") else "duration (7d, 24h), UTC date, or timestamp"
        assert values in text, path


def test_fish_completion_keeps_complete_command_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("_DOT_COMPLETE", "complete_fish")
    monkeypatch.setenv("_TYPER_COMPLETE_FISH_ACTION", "get-args")
    monkeypatch.setenv("_TYPER_COMPLETE_ARGS", "dot ")
    result = CliRunner().invoke(app, prog_name="dot")
    summaries = dict(line.split("\t", 1) for line in result.stdout.splitlines())
    assert summaries["orphan"] == "List files chezmoi deployed but no longer manages (read-only; never deletes)"
    assert not any(summary.endswith("...") for summary in summaries.values())


def test_fish_completion_keeps_long_option_help_on_one_line(monkeypatch: pytest.MonkeyPatch) -> None:
    # Rich would wrap this at an 80-column console and split one candidate in two.
    monkeypatch.setenv("COLUMNS", "40")
    monkeypatch.setenv("_DOT_COMPLETE", "complete_fish")
    monkeypatch.setenv("_TYPER_COMPLETE_FISH_ACTION", "get-args")
    monkeypatch.setenv("_TYPER_COMPLETE_ARGS", "dot agent context --")
    result = CliRunner().invoke(app, prog_name="dot")
    assert all("\t" in line for line in result.stdout.splitlines()), result.stdout
    assert "--check\tExit 1 at 5000 instruction + discovery tokens in either global or local scope" in result.stdout


def test_agent_stats_documents_every_option() -> None:
    root = get_command(app)
    assert isinstance(root, TyperGroup)
    agent = root.commands["agent"]
    assert isinstance(agent, TyperGroup)
    undocumented = [
        parameter.opts[0] for parameter in agent.commands["stats"].params if not getattr(parameter, "help", "")
    ]
    assert undocumented == []
