"""Validate canonical reviewer supagents, closed read-only host schemas, and Vale anti-slop rules."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from dot_tasks.skill_contracts import _read_utf8
from repo_helpers import ROOT, native_binary

EXPECTED_REVIEWERS = frozenset(
    {
        "fmind-review-ai",
        "fmind-review-code",
        "fmind-review-data",
        "fmind-review-design",
        "fmind-review-finops",
        "fmind-review-human",
        "fmind-review-interface",
        "fmind-review-mlops",
        "fmind-review-ops",
        "fmind-review-perf",
        "fmind-review-pitch",
        "fmind-review-security",
        "fmind-review-web",
    }
)
EXPECTED_TOP_KEYS = {"name", "description", "AGY", "CLAUDE", "COPILOT", "OPENCODE"}
EXPECTED_AGY_KEYS = {
    "subagent",
    "mainAgent",
    "model",
    "excludeDefaultComponents",
    "inheritMcp",
    "commandExecutionPolicy",
    "tools",
}
EXPECTED_AGY_TOOLS = ["view_file", "list_dir", "find_by_name", "grep_search", "finish"]
EXPECTED_CLAUDE_KEYS = {"model", "maxTurns", "tools", "disallowedTools"}
EXPECTED_CLAUDE_TOOLS = ["Read", "Glob", "Grep", "LSP"]
EXPECTED_CLAUDE_DENIED = [
    "Write",
    "Edit",
    "NotebookEdit",
    "Bash",
    "PowerShell",
    "Agent",
    "Task",
    "WebFetch",
    "WebSearch",
    "mcp__*",
]
EXPECTED_COPILOT_KEYS = {"tools"}
EXPECTED_OPENCODE_KEYS = {"mode", "steps", "permissions"}
EXPECTED_OPENCODE_RULES = [
    {"action": "*", "resource": "*", "effect": "deny"},
    {"action": "read", "resource": "*", "effect": "allow"},
    {"action": "read", "resource": "*.env", "effect": "deny"},
    {"action": "read", "resource": "*.env.*", "effect": "deny"},
    {"action": "read", "resource": "*.envrc", "effect": "deny"},
    {"action": "read", "resource": "*.env.example", "effect": "allow"},
    {"action": "glob", "resource": "*", "effect": "allow"},
    {"action": "grep", "resource": "*", "effect": "allow"},
    {"action": "list", "resource": "*", "effect": "allow"},
    {"action": "lsp", "resource": "*", "effect": "allow"},
]


def _read_safe_markdown(path: Path) -> str:
    assert not path.is_symlink(), f"{path}: symlinks are forbidden in reviewer definitions"
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    text, errors = _read_utf8(path, rel)
    assert not errors, f"{path}: {errors}"
    assert text is not None
    return text


def _split_frontmatter(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    text = _read_safe_markdown(path)
    lines = text.splitlines()
    assert lines[0] == "---", f"{path}: missing opening YAML delimiter"
    closing = lines.index("---", 1)
    metadata = yaml.safe_load("\n".join(lines[1:closing]))
    assert isinstance(metadata, dict)
    raw_body = lines[closing + 1 :]
    while raw_body and not raw_body[0].strip():
        raw_body.pop(0)
    non_empty_body = [line for line in raw_body if line.strip()]
    return metadata, raw_body, non_empty_body


def _assert_unique_str_list(value: object, label: str) -> list[str]:
    assert isinstance(value, list), f"{label}: expected list, got {type(value).__name__}"
    assert all(isinstance(item, str) for item in value), f"{label}: expected str items"
    assert len(set(value)) == len(value), f"{label}: duplicate items in {value}"
    return value


def _validate_metadata(metadata: dict[str, Any], expected_name: str) -> None:
    assert set(metadata) == EXPECTED_TOP_KEYS
    assert metadata["name"] == expected_name
    description = metadata.get("description")
    assert isinstance(description, str)
    assert 40 <= len(description) <= 190

    agy = metadata["AGY"]
    assert isinstance(agy, dict)
    assert set(agy) == EXPECTED_AGY_KEYS
    assert agy["subagent"] is True
    assert agy["mainAgent"] is True
    assert agy["model"] == "inherit"
    assert agy["excludeDefaultComponents"] is True
    assert agy["inheritMcp"] is False
    assert agy["commandExecutionPolicy"] == "off"
    assert _assert_unique_str_list(agy["tools"], "AGY.tools") == EXPECTED_AGY_TOOLS

    claude = metadata["CLAUDE"]
    assert isinstance(claude, dict)
    assert set(claude) == EXPECTED_CLAUDE_KEYS
    assert claude["model"] == "inherit"
    assert claude["maxTurns"] == 25
    assert _assert_unique_str_list(claude["tools"], "CLAUDE.tools") == EXPECTED_CLAUDE_TOOLS
    assert _assert_unique_str_list(claude["disallowedTools"], "CLAUDE.disallowedTools") == EXPECTED_CLAUDE_DENIED

    copilot = metadata["COPILOT"]
    assert isinstance(copilot, dict)
    assert set(copilot) == EXPECTED_COPILOT_KEYS
    assert _assert_unique_str_list(copilot["tools"], "COPILOT.tools") == ["read", "search"]

    opencode = metadata["OPENCODE"]
    assert isinstance(opencode, dict)
    assert set(opencode) == EXPECTED_OPENCODE_KEYS
    assert opencode["mode"] == "all"
    assert opencode["steps"] == 25
    assert opencode["permissions"] == EXPECTED_OPENCODE_RULES


def _assert_read_only_source(path: Path) -> None:
    metadata, raw_body, non_empty_body = _split_frontmatter(path)
    expected_name = path.stem if path.parent.name == "supagents" else "org-review-role"
    _validate_metadata(metadata, expected_name)
    assert len(raw_body) <= 100, f"{path.name}: keep reviewer body <= 100 lines (got {len(raw_body)})"
    assert len(non_empty_body) >= 20, f"{path.name}: body too thin (got {len(non_empty_body)} non-empty lines)"

    body_text = "\n".join(raw_body)
    assert "## Audit Rubric" in body_text
    assert "## Do Not Flag" in body_text
    assert "## Output Contract" in body_text
    assert "VERDICT: PASS | REVISE | BLOCK" in body_text
    assert "Never echo raw secret, token, or PII values" in body_text
    assert "DELETIONS:" in body_text
    assert "UNVERIFIED:" in body_text


def test_canonical_reviewer_sources_and_template_stay_bounded_and_read_only() -> None:
    source_dir = ROOT / "dot_agents/supagents"
    files = sorted(source_dir.glob("*.md"))
    assert {path.stem for path in files} == EXPECTED_REVIEWERS
    for path in [*files, ROOT / "skills/subagent/templates/reviewer.md"]:
        _assert_read_only_source(path)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda m: m.update({"mcpServers": ["evil"]}),
        lambda m: m["AGY"].update({"inheritMcp": True}),
        lambda m: m["AGY"].update({"tools": [*EXPECTED_AGY_TOOLS, "run_command"]}),
        lambda m: m["CLAUDE"].update({"permissionMode": "bypassPermissions"}),
        lambda m: m["COPILOT"].update({"mcp-servers": {"x": {}}}),
        lambda m: m["OPENCODE"].update({"permission": {"*": "allow"}}),
        lambda m: m["OPENCODE"]["permissions"].append({"action": "shell", "resource": "*", "effect": "allow"}),
    ],
    ids=[
        "shared-mcp-servers",
        "agy-inherit-mcp",
        "agy-run-command",
        "claude-bypass-permissions",
        "copilot-mcp-servers",
        "opencode-v1-permission",
        "opencode-shell-allow",
    ],
)
def test_validate_metadata_fails_closed_on_privilege_escalation(mutator: Any) -> None:
    baseline, _, _ = _split_frontmatter(ROOT / "skills/subagent/templates/reviewer.md")
    tampered = copy.deepcopy(baseline)
    mutator(tampered)
    with pytest.raises(AssertionError):
        _validate_metadata(tampered, "org-review-role")


def test_supagents_strict_check_compiled_outputs_and_chezmoi_exclusions() -> None:
    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "supagents",
            "check",
            "--strict",
            "--project",
            "--source-dir",
            "dot_agents/supagents",
            "--config",
            "supagents.yaml",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    expected_total = len(EXPECTED_REVIEWERS) * 4
    assert f"{expected_total} unchanged, 0 obsolete, 0 warnings, 0 errors" in check.stdout

    targets = yaml.safe_load((ROOT / "supagents.yaml").read_text(encoding="utf-8"))["targets"]
    expected_compiled_keys = {
        "AGY": {"name", "description", *EXPECTED_AGY_KEYS},
        "CLAUDE": {"name", "description", *EXPECTED_CLAUDE_KEYS},
        "COPILOT": {"name", "description", *EXPECTED_COPILOT_KEYS},
        "OPENCODE": {"name", "description", *EXPECTED_OPENCODE_KEYS},
    }
    for host, settings in targets.items():
        suffix = ".agent.md" if host == "COPILOT" else ".md"
        out_dir = ROOT / settings["project_path"]
        compiled = sorted(out_dir.glob(f"*{suffix}"))
        assert len(compiled) == len(EXPECTED_REVIEWERS)
        for path in compiled:
            fm, _, _ = _split_frontmatter(path)
            assert set(fm) == expected_compiled_keys[host]

    ignored = (ROOT / ".chezmoiignore").read_text(encoding="utf-8").splitlines()
    assert "supagents.yaml" in ignored
    dprint_lines = [
        line
        for line in (ROOT / "dprint.json").read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    ]
    dprint = json.loads("\n".join(dprint_lines))
    for settings in targets.values():
        assert f"{settings['project_path']}/**" in dprint["excludes"]


def test_vale_catches_ai_slop_and_handles_commonmark_edge_cases(tmp_path: Path) -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for live prose-rule verification")

    config = ROOT / "dot_config/vale/dot_vale.ini"
    slop = tmp_path / "slop.md"
    slop.write_text(
        "In today's fast-paced landscape, we delve into a seamless rollout — a game-changer.\n\n"
        "Use ```inline_triple``` carefully.\n\n"
        "Checked `loader.py` and bumped `chunk_size` in `main.tf` cleanly.\n\n" + (" ".join(["word"] * 85)) + ".\n",
        encoding="utf-8",
    )
    slop_run = subprocess.run(
        [vale, "--config", str(config), "--output=JSON", str(slop)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert slop_run.returncode == 1, slop_run.stdout + slop_run.stderr
    findings = json.loads(slop_run.stdout)[str(slop)]
    checks = {item["Check"] for item in findings}
    assert checks == {"Fmind.SlopWords", "Fmind.EmDash", "Fmind.ProseBackticks", "Fmind.ParagraphLength"}
    backtick_lines = [item["Line"] for item in findings if item["Check"] == "Fmind.ProseBackticks"]
    assert backtick_lines == [5]

    clean = tmp_path / "clean.md"
    clean.write_text(
        "---\n"
        'description: "Flags `--one`, `--two`, and `--three` in YAML frontmatter."\n'
        "---\n\n"
        "**Batch imports are healthy again: approve PR 418 before 17:00 UTC.**\n\n"
        "Peak memory stays below our 8 GB limit. Run ``cmd `a` `b` `c` `` once.\n\n"
        "> ```bash\n"
        "> echo `one` and `two` and `three`\n"
        "> ```\n\n"
        "````markdown\n"
        "```bash\n"
        "Checked `one` and `two` and `three` inside nested fence.\n"
        "```\n"
        "````\n",
        encoding="utf-8",
    )
    clean_run = subprocess.run(
        [vale, "--config", str(config), "--output=JSON", str(clean)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert clean_run.returncode == 0, clean_run.stdout + clean_run.stderr
    assert json.loads(clean_run.stdout) == {}

    html = tmp_path / "page.html"
    html.write_text(
        "<!doctype html><p>Clean outcome.</p><script>const s = `${a}` + `${b}` + `${c}`;</script>\n",
        encoding="utf-8",
    )
    html_run = subprocess.run(
        [vale, "--config", str(config), "--output=JSON", str(html)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert clean_run.returncode == 0
    assert html_run.returncode == 0, html_run.stdout + html_run.stderr
    assert json.loads(html_run.stdout) == {}
