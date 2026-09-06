from __future__ import annotations

import io
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fmind_dot.config import Config, ContextConfig
from fmind_dot.context import (
    ContextOptions,
    build_context,
    read_project_file,
    resolve_context_budget,
    run_context,
    scan_context_payload,
)
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State


class ContextRunner(Runner):
    def __init__(
        self,
        root: Path,
        *,
        gitleaks: bool = True,
        mise: bool = True,
        failures: set[tuple[str, ...]] | None = None,
        overrides: dict[tuple[str, ...], CommandResult] | None = None,
    ) -> None:
        self.root = root
        self.gitleaks = gitleaks
        self.mise = mise
        self.failures = failures or set()
        self.overrides = overrides or {}
        self.scanned: list[str] = []

    def which(self, command: str) -> Path | None:
        if (command == "mise" and self.mise) or (command == "gitleaks" and self.gitleaks):
            return Path(f"/tools/{command}")
        return None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        env: object = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult:
        del cwd, env, timeout, check
        command = tuple(args)
        if command in self.failures:
            raise DotError(f"command failed in {self.root}: {args[0]}")
        if command in self.overrides:
            return self.overrides[command]
        if command == ("git", "rev-parse", "--show-toplevel"):
            return CommandResult(f"{self.root}\n", "", 0)
        if command == ("git", "rev-parse", "HEAD"):
            return CommandResult("abc123\n", "", 0)
        if command == ("git", "status", "--short", "--branch"):
            return CommandResult("## main\n", "", 0)
        if command == ("git", "log", "-5", "--pretty=format:%h %s"):
            return CommandResult("abc123 initial", "", 0)
        if command == ("git", "ls-files", "-z"):
            return CommandResult("pyproject.toml\x00", "", 0)
        if command == ("/tools/mise", "tasks", "--json"):
            return CommandResult('[{"name":"test","description":"Run tests","aliases":["t"]}]', "", 0)
        if command == ("/tools/gitleaks", "stdin", "--no-banner", "--redact"):
            assert input_text is not None
            self.scanned.append(input_text)
            return CommandResult("", "", 0)
        raise AssertionError(f"unexpected command: {command}")


def make_state(
    root: Path,
    config: ContextConfig | None = None,
    *,
    runner: ContextRunner | None = None,
) -> tuple[State, ContextRunner]:
    runner = runner or ContextRunner(root)
    state = State(runner=runner, stdout=io.StringIO())
    state.__dict__["_config"] = Config(context=config or ContextConfig())
    return state, runner


def fixture_project(root: Path) -> None:
    (root / "AGENTS.md").write_text(f"Project at {root}\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    skill = root / "skills" / "sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample\ndescription: Sample skill.\n---\n# Sample\n",
        encoding="utf-8",
    )


def test_context_is_deterministic_bounded_and_redacts_repository_root(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    state, _ = make_state(tmp_path)
    options = ContextOptions(bytes=50_000, format="json", generated_at=datetime(2026, 1, 2, tzinfo=UTC))

    first = build_context(state, options)
    second = build_context(state, options)
    envelope = json.loads(first)

    assert first == second
    assert len(first.encode()) <= 50_000
    assert envelope["schema_version"] == "1.0"
    assert envelope["repository"] == tmp_path.name
    assert str(tmp_path) not in first
    assert [section["id"] for section in envelope["sections"]] == [
        "instructions",
        "skills",
        "git",
        "tasks",
        "dependencies",
        "failures",
    ]


def test_context_rejects_budget_too_small_for_omission_manifest(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    state, _ = make_state(tmp_path)

    with pytest.raises(DotError, match="omission manifest"):
        build_context(state, ContextOptions(bytes=10, generated_at=datetime(2026, 1, 2, tzinfo=UTC)))


def test_context_records_symlinked_instruction_as_unavailable(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-instruction.md"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "AGENTS.md").symlink_to(outside)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    state, _ = make_state(tmp_path, ContextConfig(collectors=["instructions"]))

    payload = json.loads(
        build_context(
            state,
            ContextOptions(bytes=10_000, format="json", generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
        )
    )

    section = payload["sections"][0]
    assert section["content"] == ""
    assert "regular non-symlink file" in section["error"]


def test_run_context_scans_exact_payload_before_writing(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    state, runner = make_state(tmp_path, ContextConfig(collectors=["instructions"]))
    options = ContextOptions(bytes=10_000, generated_at=datetime(2026, 1, 2, tzinfo=UTC))

    payload = run_context(state, options)

    assert runner.scanned == [payload]
    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == payload


def test_context_token_budget_reports_exact_partial_omissions(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    (tmp_path / "AGENTS.md").write_text("".join(f"instruction {index}\n" for index in range(80)), encoding="utf-8")
    config = ContextConfig(collectors=["instructions", "instructions"])
    state, _ = make_state(tmp_path, config)

    payload = build_context(
        state,
        ContextOptions(tokens=350, format="json", generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
    )
    envelope = json.loads(payload)

    assert len(payload.encode()) <= 1_400
    assert envelope["budget"] == {"effective_bytes": 1_400, "requested_tokens": 350}
    assert len(envelope["sections"]) == 1
    section = envelope["sections"][0]
    assert section["status"] == "partial"
    assert section["omitted_bytes"] > 0
    assert section["omitted_lines"] != "none"


@pytest.mark.parametrize(
    "options",
    [ContextOptions(bytes=-1), ContextOptions(tokens=-1), ContextOptions(bytes=1, tokens=1)],
)
def test_context_rejects_invalid_budget_combinations(tmp_path: Path, options: ContextOptions) -> None:
    state, _ = make_state(tmp_path)

    with pytest.raises(DotError, match="positive and mutually exclusive"):
        resolve_context_budget(state, options)


def test_context_uses_configured_default_budget(tmp_path: Path) -> None:
    state, _ = make_state(tmp_path, ContextConfig(max_bytes=12_345))

    budget = resolve_context_budget(state, ContextOptions())

    assert budget.effective_bytes == 12_345
    assert budget.requested_bytes == 0
    assert budget.requested_tokens == 0


@pytest.mark.parametrize(
    ("relative", "error"),
    [
        ("", "project-relative"),
        ("/etc/passwd", "project-relative"),
        ("../outside", "escapes project root"),
        ("missing.md", "source does not exist"),
        ("directory", "regular non-symlink file"),
        ("invalid.txt", "unreadable UTF-8"),
    ],
)
def test_context_file_reads_fail_closed_at_project_boundary(tmp_path: Path, relative: str, error: str) -> None:
    (tmp_path / "directory").mkdir()
    (tmp_path / "invalid.txt").write_bytes(b"\xff")

    with pytest.raises(DotError, match=error):
        read_project_file(tmp_path, relative)


def test_context_reports_unsafe_sources_missing_tools_and_unknown_collectors(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    config = ContextConfig(
        collectors=["tasks", "instructions", "unknown", "instructions"],
        instruction_files=["../outside", "missing.md"],
    )
    state, _ = make_state(tmp_path, config, runner=ContextRunner(tmp_path, mise=False))

    envelope = json.loads(
        build_context(
            state,
            ContextOptions(bytes=10_000, format="json", generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
        )
    )
    sections = {section["id"]: section for section in envelope["sections"]}

    assert list(sections) == ["instructions", "tasks", "unknown"]
    assert "path escapes project root" in sections["instructions"]["error"]
    assert "source does not exist" in sections["instructions"]["error"]
    assert sections["tasks"]["error"] == "mise unavailable"
    assert sections["unknown"]["error"] == "collector is not allowlisted"
    assert str(tmp_path) not in json.dumps(envelope)


def test_context_records_collector_command_failures_without_losing_manifest(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    failures = {
        ("git", "status", "--short", "--branch"),
        ("git", "log", "-5", "--pretty=format:%h %s"),
        ("git", "ls-files", "-z"),
    }
    overrides: dict[tuple[str, ...], CommandResult] = {("/tools/mise", "tasks", "--json"): CommandResult("{}", "", 0)}
    runner = ContextRunner(tmp_path, failures=failures, overrides=overrides)
    config = ContextConfig(collectors=["git", "tasks", "dependencies"])
    state, _ = make_state(tmp_path, config, runner=runner)

    envelope = json.loads(
        build_context(
            state,
            ContextOptions(bytes=10_000, format="json", generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
        )
    )
    sections = {section["id"]: section for section in envelope["sections"]}

    assert "command failed in ." in sections["git"]["error"]
    assert sections["tasks"]["error"] == "mise returned invalid task metadata"
    assert "command failed" in sections["dependencies"]["error"]
    assert all(section["fingerprint"].startswith("sha256:") for section in sections.values())


def test_context_secret_boundaries_reject_paths_and_environment_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = ContextConfig(
        sensitive_path_patterns=["private/customer"],
        sensitive_env_patterns=["CONTEXT_TEST_*"],
    )
    state, _ = make_state(tmp_path, config)

    with pytest.raises(DotError, match="sensitive path pattern"):
        scan_context_payload(state, "private/customer/data")

    monkeypatch.setenv("CONTEXT_TEST_SECRET", "very-private-value")
    with pytest.raises(DotError, match="CONTEXT_TEST_SECRET"):
        scan_context_payload(state, "token=very-private-value")


def test_context_wraps_secret_scanner_failure_without_writing(tmp_path: Path) -> None:
    fixture_project(tmp_path)
    state, _ = make_state(
        tmp_path,
        ContextConfig(collectors=["instructions"]),
        runner=ContextRunner(tmp_path, gitleaks=False),
    )

    with pytest.raises(DotError, match="context payload secret scan failed"):
        run_context(state, ContextOptions(bytes=10_000, generated_at=datetime(2026, 1, 2, tzinfo=UTC)))

    assert isinstance(state.stdout, io.StringIO)
    assert state.stdout.getvalue() == ""


@pytest.mark.parametrize(
    ("runner", "options", "error"),
    [
        (
            lambda root: ContextRunner(root, failures={("git", "rev-parse", "--show-toplevel")}),
            ContextOptions(bytes=1_000, generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
            "failed to resolve project root",
        ),
        (
            lambda root: ContextRunner(
                root,
                overrides={("git", "rev-parse", "--show-toplevel"): CommandResult("", "", 0)},
            ),
            ContextOptions(bytes=1_000, generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
            "empty project root",
        ),
        (
            lambda root: ContextRunner(root, failures={("git", "rev-parse", "HEAD")}),
            ContextOptions(bytes=1_000, generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
            "failed to fingerprint project HEAD",
        ),
        (
            ContextRunner,
            ContextOptions(bytes=1_000, format="yaml", generated_at=datetime(2026, 1, 2, tzinfo=UTC)),
            "unsupported context format",
        ),
        (
            ContextRunner,
            ContextOptions(bytes=1_000, generated_at=datetime(2026, 1, 2)),
            "timestamp must include a timezone",
        ),
    ],
)
def test_context_surfaces_boundary_errors_with_actionable_context(
    tmp_path: Path,
    runner: Callable[[Path], ContextRunner],
    options: ContextOptions,
    error: str,
) -> None:
    fixture_project(tmp_path)
    selected_runner = runner(tmp_path)
    state, _ = make_state(tmp_path, runner=selected_runner)

    with pytest.raises(DotError, match=error):
        build_context(state, options)
