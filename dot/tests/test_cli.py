from __future__ import annotations

import json
import os
import re
import runpy
import shlex
import sqlite3
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

import fmind_dot.cli as cli
from fmind_dot.cli import app, build_parser
from fmind_dot.command import FISH_COMPLETION, Parser, candidates
from fmind_dot.errors import CancelledError, DotError
from fmind_dot.process import Runner
from tests.fakes import CliRunner, native_binary

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_root_help_exposes_python_first_command_tree() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    # Repository tasks and release gates call `dot completion`; it stays out of everyday help.
    assert not re.search(r"^\s*completion\s", result.stdout, flags=re.MULTILINE)


def test_fish_completion_callback_works_in_fresh_process(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "fmind_dot", "agent"],
        cwd=tmp_path,
        env={**os.environ, "_DOT_COMPLETE": "s"},
        capture_output=True,
        text=True,
        # Returns as soon as the CLI exits; a fresh interpreter can take seconds under load.
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "session\tManage agent session logs\n"
        "stats\tSync changed sessions (unless --no-sync), then report prompts, tokens, costs, and API equivalents\n"
    )
    assert result.stderr == ""


def test_fish_script_completes_through_the_installed_callback(tmp_path: Path) -> None:
    fish = native_binary("fish")
    if fish is None:
        pytest.skip("fish is not installed")
    # A stand-in `dot` on PATH runs this checkout, so the script is exercised exactly as Fish loads it.
    calls = tmp_path / "calls.log"
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/dot").write_text(
        f'#!/bin/sh\necho x >> {shlex.quote(str(calls))}\nexec {shlex.quote(sys.executable)} -m fmind_dot "$@"\n'
    )
    (tmp_path / "bin/dot").chmod(0o755)
    (tmp_path / "dot.fish").write_text(FISH_COMPLETION)

    (tmp_path / "custom.yaml").write_text("")
    probes = ("dot do", "dot agent ", "dot agent stats --agent cl", "dot status --j", "dot --config cust")
    script = f"source {tmp_path}/dot.fish; " + "; ".join(
        f"echo ===; complete --do-complete={shlex.quote(line)}" for line in probes
    )
    result = subprocess.run(
        [str(fish), "--no-config", "--command", script],
        env={**os.environ, "PATH": f"{tmp_path}/bin{os.pathsep}{os.environ['PATH']}"},
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    outputs = [block.splitlines() for block in result.stdout.split("===\n")[1:]]
    assert "doctor\tCheck local workstation health; --deep also probes authentication" in outputs[0]
    assert [line.split("\t")[0] for line in outputs[1]] == ["context", "doctor", "session", "stats"]
    assert outputs[2] == ["claude"]
    assert "--json\tEmit structured JSON" in outputs[3]
    # Without candidates Fish falls back to file names.
    assert outputs[4] == ["custom.yaml"]
    assert len(calls.read_text().splitlines()) == len(probes)


def test_subcommand_help_displays_canonical_commands() -> None:
    result = runner.invoke(app, ["config", "--help"])

    assert result.exit_code == 0
    for command in ("edit", "path", "show"):
        assert command in result.stdout
    assert not re.search(r"\([a-z]\)", result.stdout)


def test_root_command_tree_has_only_the_canonical_runtime_commands() -> None:
    root = build_parser()
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
    assert {name for name, child in root.children.items() if not child.hidden} == expected - {"completion"}
    assert set(root.children) == expected


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
                "orphan",
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
def test_help_lists_commands_alphabetically(path: list[str], names: list[str]) -> None:
    result = runner.invoke(app, [*path, "--help"])
    assert result.exit_code == 0
    rows = [match.group(1) for match in re.finditer(r"(?m)^    (\S+)\s", result.stdout)]
    assert rows == names


def test_agent_command_tree_keeps_hooks_internal_and_sync_as_the_only_capture() -> None:
    agent = build_parser().children["agent"]
    assert {name for name, child in agent.children.items() if not child.hidden} == {
        "context",
        "doctor",
        "session",
        "stats",
    }
    assert agent.children["hook"].hidden
    assert set(agent.children["hook"].children) == {"notify"}
    assert set(agent.children["session"].children) == {"list", "show", "sync"}


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
def test_documented_dot_examples_parse(example: str) -> None:
    # --help stops after parsing, so unknown commands and options fail without running anything.
    result = runner.invoke(app, [*shlex.split(example)[1:], "--help"])

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("arguments", [["--version"], ["-V"]])
def test_version_matches_distribution(arguments: list[str]) -> None:
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
    invalid.write_text("pull:\n  directories: lots\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(invalid), "doctor"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert f"dot: invalid config file at {invalid} (1 validation error(s)): pull.directories:" in captured.err
    assert "fix it with: dot config edit" in captured.err
    assert "lots" not in captured.err


@pytest.mark.parametrize(
    "content",
    ["prune: [\n", "agent: " + "[" * 1200 + "SYNTHETIC_PRIVATE_VALUE" + "]" * 1200 + "\n"],
    ids=["syntax", "deep-nesting"],
)
def test_main_reports_malformed_explicit_yaml_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text(content, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dot", "--config", str(malformed), "doctor"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.out == ""
    assert f"dot: failed to parse config file at {malformed}:" in captured.err
    assert "Traceback" not in captured.err
    assert "SYNTHETIC_PRIVATE_VALUE" not in captured.err


@pytest.mark.parametrize(
    "content",
    [
        "api_token: SYNTHETIC_PRIVATE_VALUE\n",
        "pull:\n  directories: SYNTHETIC_PRIVATE_VALUE\n",
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
    path.write_text("trust:\n  github_owners: [example]\n", encoding="utf-8")

    result = runner.invoke(app, ["--config", str(path), "config", "show"])

    assert result.exit_code == 0
    rendered = yaml.safe_load(result.stdout)
    assert rendered["trust"]["github_owners"] == ["example"]
    assert rendered["pull"]["directories"] == ["~/fmind"]
    assert "git" in rendered["doctor"]["tools"]


def test_config_path_expands_the_current_home(tmp_path: Path) -> None:

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
        Path(arguments[-1]).write_text("trust:\n  github_owners: [example]\n", encoding="utf-8")
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

    monkeypatch.setenv("EDITOR", 'vim "unterminated')
    malformed_editor = runner.invoke(app, ["--config", str(path), "config", "edit"])
    assert malformed_editor.exit_code == 1
    assert isinstance(malformed_editor.exception, DotError)
    assert str(malformed_editor.exception).startswith("invalid EDITOR value:")


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

    monkeypatch.setattr(cli, "app", fail)

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
        (["--unknown-option"], 2, "unrecognized arguments: --unknown-option"),
        (["unknown-command"], 2, "invalid choice: 'unknown-command'"),
        (["help", "unknown-command"], 2, "invalid choice: 'help'"),
        (["agent", "sesion"], 2, "maybe you meant 'session'?"),  # typos: ignore-line
        (["agent", "stats", "--since", "never"], 2, "dot agent stats: error: --since: expected a duration"),
        (["status", "--js"], 2, "unrecognized arguments: --js"),
    ],
)
def test_python_module_entrypoint_preserves_parser_exit_codes(
    arguments: list[str],
    expected_exit: int,
    expected_error: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["dot", *arguments])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("fmind_dot", run_name="__main__")

    captured = capsys.readouterr()
    assert exit_info.value.code == expected_exit
    assert captured.out == ""
    assert expected_error in captured.err
    assert "Traceback" not in captured.err


def test_main_maps_keyboard_interrupt_to_shell_exit_130(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "app", interrupt)

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 130
    assert captured.out == ""
    assert captured.err == "Cancelled.\n"


def test_main_reports_keyboard_interrupt_raised_inside_a_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupt(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "dump_config", interrupt)
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

    monkeypatch.setattr(cli, "app", fail)

    with pytest.raises(RuntimeError, match="programmer error"):
        cli.main()


@pytest.mark.parametrize(
    "path",
    [
        [],
        ["config"],
        ["agent"],
        ["agent", "session"],
        ["setup"],
    ],
)
def test_bare_groups_show_help_successfully_without_actions(path: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Runner, "which", lambda *_: pytest.fail("help must not inspect or run native tools"))
    result = runner.invoke(app, path)
    assert result.exit_code == 0, result.output
    assert "usage:" in result.stdout
    assert "commands:" in result.stdout


def walk(parser: Parser, path: str = "dot") -> list[tuple[str, Parser]]:
    """Every command and group with its full invocation path."""
    return [
        (path, parser),
        *(item for name, child in parser.children.items() for item in walk(child, f"{path} {name}")),
    ]


def test_every_command_and_option_has_a_description() -> None:
    for path, parser in walk(build_parser()):
        assert parser.summary.strip(), f"missing description: {path}"
        for argument in parser.arguments:
            assert (argument.help or "").strip(), f"missing help: {path} {argument.dest}"


def test_every_parser_renders_its_help() -> None:
    # argparse formats help strings with %, so a stray percent sign would only fail when help is shown.
    for path, parser in walk(build_parser()):
        assert parser.format_help().startswith(f"usage: {path} "), path


def test_commands_register_alphabetically_so_help_lists_them_in_order() -> None:
    for path, parser in walk(build_parser()):
        assert list(parser.children) == sorted(parser.children), path


def test_date_filters_share_values_and_name_their_time_basis() -> None:
    help_by_path = {
        f"{path} {argument.option_strings[0]}": argument.help or ""
        for path, parser in walk(build_parser())
        for argument in parser.arguments
        if argument.dest in {"since", "until"}
    }
    assert help_by_path["dot agent session list --since"].startswith("Ingested since")
    assert help_by_path["dot agent stats --until"].startswith("Active until")
    assert help_by_path["dot agent session sync --since"].startswith("Only sources modified since")
    for path, text in help_by_path.items():
        values = "UTC date (whole day)" if path.endswith("--until") else "duration (7d, 24h), UTC date, or timestamp"
        assert values in text, path


def test_fish_candidates_keep_complete_summaries_and_hide_internal_commands() -> None:
    summaries = dict(candidates(build_parser(), [""]))
    assert summaries["orphan"] == "List files chezmoi deployed but no longer manages (read-only; never deletes)"
    assert "completion" not in summaries
    assert "hook" not in dict(candidates(build_parser(), ["agent", ""]))


def test_fish_candidates_complete_options_choices_and_nothing_after_a_separator() -> None:
    root = build_parser()
    options = dict(candidates(root, ["agent", "context", "--"]))
    assert options["--check"] == (
        "Exit 1 at 5000 instruction + discovery tokens in either global or local scope, or on duplicate skill names"
    )
    assert [value for value, _ in candidates(root, ["agent", "stats", "--agent", "c"])] == [
        "claude",
        "copilot",
        "codex",
    ]
    assert [value for value, _ in candidates(root, ["agent", "stats", "--agent=c"])] == [
        "--agent=claude",
        "--agent=copilot",
        "--agent=codex",
    ]
    assert [value for value, _ in candidates(root, ["agent", "stats", "--agent=claude", "--mon"])] == ["--monthly"]
    # A value-taking option consumes the next word: `stats` here is a project, not a command.
    assert [value for value, _ in candidates(root, ["agent", "stats", "--project", "session", "--mon"])] == [
        "--monthly"
    ]
    assert [value for value, _ in candidates(root, ["login", "g"])] == ["gcp", "github"]
    assert candidates(root, ["cache", "uv", ""]) == []
    paired = Parser(prog="dot")
    paired.add_argument("first", choices=("alpha", "beta"))
    paired.add_argument("second", choices=("stop", "ready", "needs-input"))
    assert [value for value, _ in candidates(paired, [""])] == ["alpha", "beta"]
    assert [value for value, _ in candidates(paired, ["alpha", ""])] == ["stop", "ready", "needs-input"]
    assert candidates(paired, ["alpha", "stop", ""]) == []
    assert candidates(root, ["secret", "run", "NAME", "--", "py"]) == []
    assert candidates(root, ["--config", ""]) == []


def test_main_answers_the_completion_callback_without_running_a_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("_DOT_COMPLETE", "tr")
    monkeypatch.setattr(sys, "argv", ["dot"])
    monkeypatch.setattr(cli, "app", lambda: pytest.fail("completion must not run a command"))
    cli.main()
    assert capsys.readouterr().out.startswith("trust\tPre-accept folder trust")


def test_main_reports_a_declined_confirmation_as_a_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def decline() -> None:
        raise CancelledError

    monkeypatch.setattr(cli, "app", decline)
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 1
    assert capsys.readouterr().err == "Cancelled.\n"


def test_main_exits_silently_on_broken_pipe(tmp_path: Path) -> None:
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import fmind_dot.cli as cli, sys; cli.app = lambda: sys.stdout.write('x' * 65536); cli.main()",
            ],
            cwd=tmp_path,
            stdout=write_fd,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        os.close(write_fd)
    assert result.returncode == 141
    assert result.stderr == ""


@pytest.mark.parametrize("command", [["pull"], ["agent", "stats"], ["login"]])
def test_help_works_with_invalid_config(command: list[str], tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text("pull:\n  typo: true\n")
    result = runner.invoke(app, ["--config", str(config), *command, "--help"])
    assert result.exit_code == 0
    assert "usage:" in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ["agent", "session", "show"],
        ["agent", "stats", "--since", "invalid"],
        ["agent", "stats", "--since", "2026-09-16", "--until", "2026-09-15"],
        ["agent", "session", "list", "--since", "2026-09-16", "--until", "2026-09-15"],
        ["agent", "stats", "--sessions", "--limit", "-1"],
        ["agent", "stats", "--limit", "10"],
        ["agent", "session", "list", "--limit", "-1"],
        ["agent", "stats", "--tokens-only", "--prompts-only"],
    ],
)
def test_usage_errors_exit_two(arguments: list[str]) -> None:
    assert runner.invoke(app, arguments).exit_code == 2


def test_login_dry_run_names_every_provider() -> None:
    result = runner.invoke(app, ["login", "--dry-run"])
    assert result.exit_code == 0
    assert "gh auth login" in result.stdout
    assert "gws auth login" in result.stdout
    assert "gcloud auth login" in result.stdout


def test_invalid_config_still_blocks_archive_reads(tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text("pull:\n  typo: true\n")
    result = runner.invoke(app, ["--config", str(config), "agent", "session", "show", "missing"])
    assert result.exit_code == 1
    assert "validation error" in str(result.exception)
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("command", "key"),
    [
        (["agent", "session", "list"], "sessions"),
        (["agent", "stats", "--sessions"], "records"),
        (["pull"], "repositories"),
    ],
)
def test_empty_json_has_versioned_envelope(command: list[str], key: str) -> None:
    result = runner.invoke(app, [*command, "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document["schema"].startswith("dot.")
    assert document[key] == []
