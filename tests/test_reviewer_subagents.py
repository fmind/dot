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
        *(
            f"fmind-review-{role}"
            for role in (
                "ai",
                "arch",
                "code",
                "compliance",
                "data",
                "design",
                "docs",
                "factcheck",
                "finops",
                "human",
                "interface",
                "mlops",
                "ops",
                "perf",
                "pitch",
                "security",
                "web",
            )
        ),
    }
)
WEB_ENABLED_REVIEWERS = frozenset({"fmind-review-factcheck"})
EXPECTED_PARTIAL_KEYS = {"AGY", "CLAUDE", "COPILOT", "OPENCODE"}
EXPECTED_TOP_KEYS = {"name", "description", *EXPECTED_PARTIAL_KEYS}
EXPECTED_CHILD_KEYS = {"extends", "name", "description"}
EXPECTED_FACTCHECK_CHILD_KEYS = EXPECTED_CHILD_KEYS | EXPECTED_PARTIAL_KEYS
EXPECTED_HOST_KEYS = {
    "AGY": {
        "subagent",
        "mainAgent",
        "model",
        "excludeDefaultComponents",
        "inheritMcp",
        "commandExecutionPolicy",
        "tools",
    },
    "CLAUDE": {"model", "maxTurns", "omitClaudeMd", "tools", "disallowedTools"},
    "COPILOT": {"tools"},
    "OPENCODE": {"mode", "steps", "permissions"},
}
EXPECTED_AGY_TOOLS = ["view_file", "list_dir", "find_by_name", "grep_search", "finish"]
EXPECTED_FACTCHECK_AGY_TOOLS = [*EXPECTED_AGY_TOOLS[:-1], "read_url_content", "search_web", "finish"]
EXPECTED_CLAUDE_TOOLS = ["Read", "Glob", "Grep", "LSP"]
EXPECTED_FACTCHECK_CLAUDE_TOOLS = [*EXPECTED_CLAUDE_TOOLS, "WebFetch", "WebSearch"]
BASE_CLAUDE_DENIED = ["Write", "Edit", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task"]
PORTABLE_CLAUDE_READ_DENIES = [
    "Read(.env*)",
    "Read(*.env*)",
    "Read(*.age)",
    "Read(*.pem)",
    "Read(*.key)",
    "Read(*.p12)",
    "Read(*.pfx)",
    "Read(~/.ssh/**)",
]
WORKSTATION_CLAUDE_READ_DENIES = [
    *PORTABLE_CLAUDE_READ_DENIES,
    "Read(~/.config/dot/secrets/**)",
    "Read(~/.config/chezmoi/key.txt)",
    "Read(~/.config/bf/**)",
    "Read(~/.local/share/opencode/auth.json)",
    "Read(~/.cache/huggingface/token)",
    "Read(~/.kaggle/**)",
    "Read(~/.sonar/sonarqube-cli/tokens.json)",
    "Read(~/.config/configstore/firebase-tools.json)",
    "Read(~/.config/pup/**)",
    "Read(~/.config/gh/hosts.yml)",
]
EXPECTED_TEMPLATE_CLAUDE_DENIED = [*BASE_CLAUDE_DENIED, "WebFetch", "WebSearch", "mcp__*", *PORTABLE_CLAUDE_READ_DENIES]
EXPECTED_CLAUDE_DENIED = [*BASE_CLAUDE_DENIED, "WebFetch", "WebSearch", "mcp__*", *WORKSTATION_CLAUDE_READ_DENIES]
EXPECTED_FACTCHECK_CLAUDE_DENIED = [*BASE_CLAUDE_DENIED, "mcp__*", *WORKSTATION_CLAUDE_READ_DENIES]
PORTABLE_OPENCODE_PATTERNS = ("*.env*", "*.age", "*.pem", "*.key", "*.p12", "*.pfx", "~/.ssh/*")
WORKSTATION_OPENCODE_PATTERNS = (
    *PORTABLE_OPENCODE_PATTERNS,
    "~/.config/dot/secrets/*",
    "~/.config/chezmoi/key.txt",
    "~/.local/share/opencode/auth.json",
    "~/.config/bf/*",
    "~/.cache/huggingface/token",
    "~/.kaggle/*",
    "~/.sonar/sonarqube-cli/tokens.json",
    "~/.config/configstore/firebase-tools.json",
    "~/.config/pup/*",
    "~/.config/gh/hosts.yml",
)


def _opencode_rules(patterns: tuple[str, ...], *, allow_web: bool = False) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = [
        {"action": "*", "resource": "*", "effect": "deny"},
        {"action": "read", "resource": "*", "effect": "allow"},
        *({"action": "read", "resource": p, "effect": "deny"} for p in patterns),
        {"action": "read", "resource": "*.env.example", "effect": "allow"},
        {"action": "glob", "resource": "*", "effect": "allow"},
        {"action": "grep", "resource": "*", "effect": "allow"},
        *({"action": "grep", "resource": p, "effect": "deny"} for p in patterns),
        {"action": "grep", "resource": "*.env.example", "effect": "allow"},
        {"action": "list", "resource": "*", "effect": "allow"},
        {"action": "lsp", "resource": "*", "effect": "allow"},
    ]
    if allow_web:
        rules += [
            {"action": "webfetch", "resource": "*", "effect": "allow"},
            {"action": "websearch", "resource": "*", "effect": "allow"},
        ]
    return rules


EXPECTED_TEMPLATE_OPENCODE_RULES = _opencode_rules(PORTABLE_OPENCODE_PATTERNS)
EXPECTED_OPENCODE_RULES = _opencode_rules(WORKSTATION_OPENCODE_PATTERNS)
EXPECTED_FACTCHECK_OPENCODE_RULES = _opencode_rules(WORKSTATION_OPENCODE_PATTERNS, allow_web=True)


def _split_frontmatter(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    assert not path.is_symlink(), f"{path}: symlinks are forbidden in reviewer definitions"
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    text, errors = _read_utf8(path, rel)
    assert not errors, f"{path}: {errors}"
    assert text is not None
    lines = text.splitlines()
    assert lines[0] == "---", f"{path}: missing opening YAML delimiter"
    closing = lines.index("---", 1)
    metadata = yaml.safe_load("\n".join(lines[1:closing]))
    assert isinstance(metadata, dict)
    raw_body = lines[closing + 1 :]
    while raw_body and not raw_body[0].strip():
        raw_body.pop(0)
    return metadata, raw_body, [line for line in raw_body if line.strip()]


def _assert_unique_str_list(value: object, label: str) -> list[str]:
    assert isinstance(value, list), f"{label}: expected list, got {type(value).__name__}"
    assert all(isinstance(item, str) for item in value), f"{label}: expected str items"
    assert len(set(value)) == len(value), f"{label}: duplicate items in {value}"
    return value


def _validate_host_block(host: str, block: Any, *, allow_web: bool = False, template: bool = False) -> None:
    assert isinstance(block, dict), f"{host}: expected mapping"
    assert set(block) == EXPECTED_HOST_KEYS[host]
    if host == "AGY":
        assert block["subagent"] is True
        assert block["mainAgent"] is True
        assert block["model"] == "inherit"
        assert block["excludeDefaultComponents"] is True
        assert block["inheritMcp"] is False
        assert block["commandExecutionPolicy"] == "off"
        tools = EXPECTED_FACTCHECK_AGY_TOOLS if allow_web else EXPECTED_AGY_TOOLS
        assert _assert_unique_str_list(block["tools"], "AGY.tools") == tools
    elif host == "CLAUDE":
        assert block["model"] == "inherit"
        assert block["maxTurns"] == 25
        assert block["omitClaudeMd"] is True
        tools = EXPECTED_FACTCHECK_CLAUDE_TOOLS if allow_web else EXPECTED_CLAUDE_TOOLS
        base_denied = EXPECTED_TEMPLATE_CLAUDE_DENIED if template else EXPECTED_CLAUDE_DENIED
        denied = EXPECTED_FACTCHECK_CLAUDE_DENIED if allow_web else base_denied
        assert _assert_unique_str_list(block["tools"], "CLAUDE.tools") == tools
        assert _assert_unique_str_list(block["disallowedTools"], "CLAUDE.disallowedTools") == denied
    elif host == "COPILOT":
        tools = ["read", "search", "web"] if allow_web else ["read", "search"]
        assert _assert_unique_str_list(block["tools"], "COPILOT.tools") == tools
    elif host == "OPENCODE":
        assert block["mode"] == "all"
        assert block["steps"] == 25
        rules = (
            EXPECTED_TEMPLATE_OPENCODE_RULES
            if template
            else (EXPECTED_FACTCHECK_OPENCODE_RULES if allow_web else EXPECTED_OPENCODE_RULES)
        )
        assert block["permissions"] == rules
    else:  # pragma: no cover
        raise AssertionError(f"Unsupported host: {host}")


def _validate_host_blocks(metadata: dict[str, Any], *, allow_web: bool = False, template: bool = False) -> None:
    for host in EXPECTED_PARTIAL_KEYS:
        _validate_host_block(host, metadata[host], allow_web=allow_web, template=template)


def _validate_metadata(
    metadata: dict[str, Any], expected_name: str, *, allow_web: bool = False, template: bool = False
) -> None:
    assert set(metadata) == EXPECTED_TOP_KEYS
    assert metadata["name"] == expected_name
    desc = metadata.get("description")
    assert isinstance(desc, str)
    assert 40 <= len(desc) <= 190
    _validate_host_blocks(metadata, allow_web=allow_web, template=template)


def _assert_contract_body(name: str, raw_body: list[str], non_empty_body: list[str]) -> None:
    assert len(raw_body) <= 80, f"{name}: keep reviewer body <= 80 lines (got {len(raw_body)})"
    assert len(non_empty_body) >= 20, f"{name}: body too thin (got {len(non_empty_body)} non-empty lines)"
    body_text = "\n".join(raw_body)
    assert "{{BODY}}" not in body_text
    assert "## Audit Rubric" in body_text
    assert "## Do Not Flag" in body_text
    assert "**Calibration**:" in body_text
    assert body_text.count("## Output Contract") == 1
    assert "VERDICT: PASS | REVISE | BLOCK" in body_text
    assert "Never echo raw secret, token, or PII values" in body_text
    assert "DELETIONS:" in body_text
    assert "UNVERIFIED:" in body_text


def _validate_child_source(stem: str, meta: dict[str, Any], raw_body: list[str]) -> None:
    allow_web = stem in WEB_ENABLED_REVIEWERS
    expected_keys = EXPECTED_FACTCHECK_CHILD_KEYS if allow_web else EXPECTED_CHILD_KEYS
    assert set(meta) == expected_keys, f"{stem}: unexpected frontmatter keys {set(meta)}"
    assert meta["extends"] == "_reviewer"
    assert meta["name"] == stem
    desc = meta.get("description")
    assert isinstance(desc, str)
    assert 40 <= len(desc) <= 190
    if allow_web:
        for host in EXPECTED_PARTIAL_KEYS:
            assert isinstance(meta[host], dict), f"{stem}.{host}: expected mapping"
        assert set(meta["AGY"]) == {"tools"}
        assert _assert_unique_str_list(meta["AGY"]["tools"], "AGY.tools") == EXPECTED_FACTCHECK_AGY_TOOLS
        assert set(meta["CLAUDE"]) == {"tools", "disallowedTools"}
        assert _assert_unique_str_list(meta["CLAUDE"]["tools"], "CLAUDE.tools") == EXPECTED_FACTCHECK_CLAUDE_TOOLS
        assert (
            _assert_unique_str_list(meta["CLAUDE"]["disallowedTools"], "CLAUDE.disallowedTools")
            == EXPECTED_FACTCHECK_CLAUDE_DENIED
        )
        assert set(meta["COPILOT"]) == {"tools"}
        assert _assert_unique_str_list(meta["COPILOT"]["tools"], "COPILOT.tools") == ["read", "search", "web"]
        assert set(meta["OPENCODE"]) == {"permissions"}
        assert meta["OPENCODE"]["permissions"] == EXPECTED_FACTCHECK_OPENCODE_RULES
    body_text = "\n".join(raw_body)
    assert "{{BODY}}" not in body_text
    assert "## Output Contract" not in body_text
    assert "## Audit Rubric" in body_text
    assert "## Do Not Flag" in body_text
    assert "**Calibration**:" in body_text
    if allow_web:
        assert "Privacy-Safe & SSRF-Safe Web Lookup" in body_text


def test_canonical_reviewer_sources_partial_and_template_stay_bounded_and_read_only() -> None:
    source_dir = ROOT / "dot_agents/supagents"
    assert sorted(p.name for p in source_dir.glob("_*")) == ["_reviewer.md"]
    partial_meta, partial_body, _ = _split_frontmatter(source_dir / "_reviewer.md")
    assert set(partial_meta) == EXPECTED_PARTIAL_KEYS
    _validate_host_blocks(partial_meta, allow_web=False)
    partial_text = "\n".join(partial_body)
    assert "{{BODY}}" in partial_text
    assert "## Output Contract" in partial_text
    assert "VERDICT: PASS | REVISE | BLOCK" in partial_text

    files = sorted(p for p in source_dir.glob("*.md") if not p.name.startswith("_"))
    assert {path.stem for path in files} == EXPECTED_REVIEWERS
    for path in files:
        meta, raw_body, _ = _split_frontmatter(path)
        _validate_child_source(path.stem, meta, raw_body)

    template = ROOT / "skills/subagent/templates/reviewer.md"
    tmeta, traw, tnonempty = _split_frontmatter(template)
    _validate_metadata(tmeta, "org-review-role", allow_web=False, template=True)
    _assert_contract_body(template.name, traw, tnonempty)


@pytest.mark.parametrize(
    ("allow_web", "template", "mutator"),
    [
        pytest.param(False, False, lambda m: m.update({"mcpServers": ["evil"]}), id="shared-mcp-servers"),
        pytest.param(False, False, lambda m: m["AGY"].update({"inheritMcp": True}), id="agy-inherit-mcp"),
        pytest.param(False, False, lambda m: m["AGY"].update({"commandExecutionPolicy": "auto"}), id="agy-cmd-auto"),
        pytest.param(False, False, lambda m: m["AGY"].update({"excludeDefaultComponents": False}), id="agy-defaults"),
        pytest.param(
            False, False, lambda m: m["AGY"].update({"tools": [*EXPECTED_AGY_TOOLS, "run_command"]}), id="agy-sh"
        ),
        pytest.param(False, False, lambda m: m["AGY"].update({"tools": EXPECTED_FACTCHECK_AGY_TOOLS}), id="agy-web"),
        pytest.param(False, False, lambda m: m["CLAUDE"].update({"permissionMode": "bypassPermissions"}), id="cl-perm"),
        pytest.param(False, False, lambda m: m["CLAUDE"].update({"omitClaudeMd": False}), id="cl-creator-md"),
        pytest.param(
            False, False, lambda m: m["CLAUDE"].update({"tools": EXPECTED_FACTCHECK_CLAUDE_TOOLS}), id="cl-web"
        ),
        pytest.param(False, False, lambda m: m["COPILOT"].update({"mcp-servers": {"x": {}}}), id="cp-mcp"),
        pytest.param(False, False, lambda m: m["COPILOT"].update({"tools": ["read", "search", "web"]}), id="cp-web"),
        pytest.param(False, False, lambda m: m["OPENCODE"].update({"permission": {"*": "allow"}}), id="oc-v1"),
        pytest.param(
            False,
            False,
            lambda m: m["OPENCODE"].update({"permissions": EXPECTED_FACTCHECK_OPENCODE_RULES}),
            id="oc-web",
        ),
        pytest.param(
            False,
            False,
            lambda m: m["OPENCODE"]["permissions"].append({"action": "shell", "resource": "*", "effect": "allow"}),
            id="oc-sh",
        ),
        pytest.param(
            False,
            False,
            lambda m: m["OPENCODE"]["permissions"].remove({"action": "grep", "resource": "*.age", "effect": "deny"}),
            id="oc-grep-age",
        ),
        pytest.param(
            False,
            False,
            lambda m: m["OPENCODE"]["permissions"].remove({"action": "read", "resource": "*.age", "effect": "deny"}),
            id="oc-read-age",
        ),
        pytest.param(
            False,
            True,
            lambda m: m["OPENCODE"]["permissions"].append({"action": "read", "resource": "*", "effect": "allow"}),
            id="tpl-oc-read",
        ),
        pytest.param(True, False, lambda m: m["CLAUDE"].update({"disallowedTools": ["Write"]}), id="fc-cl-deny"),
        pytest.param(True, False, lambda m: m["CLAUDE"].update({"omitClaudeMd": False}), id="fc-cl-md"),
        pytest.param(
            True,
            False,
            lambda m: m["AGY"].update({"tools": [*EXPECTED_FACTCHECK_AGY_TOOLS, "run_command"]}),
            id="fc-agy-sh",
        ),
    ],
)
def test_validate_metadata_fails_closed_on_privilege_escalation(allow_web: bool, template: bool, mutator: Any) -> None:
    src = (
        "skills/subagent/templates/reviewer.md"
        if template
        else "private_dot_gemini/private_config/agents/fmind-review-code.md"
    )
    baseline, _, _ = _split_frontmatter(ROOT / src)
    tampered: dict[str, Any]
    if template:
        tampered = copy.deepcopy(baseline)
    else:
        claude, _, _ = _split_frontmatter(ROOT / "private_dot_claude/agents/fmind-review-code.md")
        copilot, _, _ = _split_frontmatter(ROOT / "private_dot_copilot/agents/fmind-review-code.agent.md")
        opencode, _, _ = _split_frontmatter(ROOT / "dot_config/private_opencode/agents/fmind-review-code.md")
        tampered = {
            "name": "fmind-review-code",
            "description": baseline["description"],
            "AGY": {k: v for k, v in baseline.items() if k not in {"name", "description"}},
            "CLAUDE": {k: v for k, v in claude.items() if k not in {"name", "description"}},
            "COPILOT": {k: v for k, v in copilot.items() if k not in {"name", "description"}},
            "OPENCODE": {k: v for k, v in opencode.items() if k not in {"name", "description"}},
        }
    if allow_web:
        tampered["AGY"]["tools"] = list(EXPECTED_FACTCHECK_AGY_TOOLS)
        tampered["CLAUDE"]["tools"] = list(EXPECTED_FACTCHECK_CLAUDE_TOOLS)
        tampered["CLAUDE"]["disallowedTools"] = list(EXPECTED_FACTCHECK_CLAUDE_DENIED)
        tampered["COPILOT"]["tools"] = ["read", "search", "web"]
        tampered["OPENCODE"]["permissions"] = list(EXPECTED_FACTCHECK_OPENCODE_RULES)
    mutator(tampered)
    with pytest.raises(AssertionError):
        _validate_metadata(tampered, str(tampered["name"]), allow_web=allow_web, template=template)


@pytest.mark.parametrize(
    ("stem", "mutator"),
    [
        pytest.param(
            "fmind-review-code", lambda m: m.update({"AGY": {"tools": EXPECTED_FACTCHECK_AGY_TOOLS}}), id="non-fc"
        ),
        pytest.param("fmind-review-factcheck", lambda m: m.update({"AGY": ["tools"]}), id="fc-non-dict"),
        pytest.param("fmind-review-factcheck", lambda m: m["AGY"].update({"inheritMcp": True}), id="fc-mcp"),
        pytest.param("fmind-review-factcheck", lambda m: m["AGY"].update({"APPEND_BODY": "extra"}), id="fc-append"),
        pytest.param("fmind-review-factcheck", lambda m: m["AGY"].update({"OUTPUT": "evil.md"}), id="fc-output"),
        pytest.param("fmind-review-factcheck", lambda m: m["CLAUDE"].update({"maxTurns": 99}), id="fc-cl-turns"),
        pytest.param("fmind-review-factcheck", lambda m: m["OPENCODE"].update({"steps": 99}), id="fc-oc-steps"),
    ],
)
def test_validate_child_source_fails_closed_on_override_escalation(stem: str, mutator: Any) -> None:
    meta, raw_body, _ = _split_frontmatter(ROOT / f"dot_agents/supagents/{stem}.md")
    tampered = copy.deepcopy(meta)
    mutator(tampered)
    with pytest.raises(AssertionError):
        _validate_child_source(stem, tampered, raw_body)


def test_supagents_strict_check_and_compiled_outputs() -> None:
    cmd = [
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
    ]
    check = subprocess.run(
        cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert f"{len(EXPECTED_REVIEWERS) * 4} unchanged, 0 obsolete, 0 warnings, 0 errors" in check.stdout

    targets = yaml.safe_load((ROOT / "supagents.yaml").read_text(encoding="utf-8"))["targets"]
    for host, settings in targets.items():
        suffix = ".agent.md" if host == "COPILOT" else ".md"
        out_dir = ROOT / settings["project_path"]
        entries = sorted(out_dir.rglob("*"))
        assert all(
            not p.is_symlink() and p.is_file() and p.parent == out_dir and p.name.endswith(suffix) for p in entries
        )
        assert {p.name.removesuffix(suffix) for p in entries} == EXPECTED_REVIEWERS
        for path in entries:
            stem = path.name.removesuffix(suffix)
            fm, raw_body, non_empty_body = _split_frontmatter(path)
            assert fm.get("name") == stem
            assert isinstance(fm.get("description"), str)
            assert 40 <= len(fm["description"]) <= 190
            _validate_host_block(
                host,
                {k: v for k, v in fm.items() if k not in {"name", "description"}},
                allow_web=stem in WEB_ENABLED_REVIEWERS,
            )
            _assert_contract_body(f"{host}/{path.name}", raw_body, non_empty_body)


def test_supagents_config_and_outputs_excluded_from_chezmoi_and_dprint() -> None:
    targets = yaml.safe_load((ROOT / "supagents.yaml").read_text(encoding="utf-8"))["targets"]
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


def _run_vale(vale: Path, config: Path, target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(vale), "--config", str(config), "--output=JSON", str(target)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


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
    slop_run = _run_vale(vale, config, slop)
    assert slop_run.returncode == 1, slop_run.stdout + slop_run.stderr
    findings = json.loads(slop_run.stdout)[str(slop)]
    assert {item["Check"] for item in findings} == {
        "Fmind.SlopWords",
        "Fmind.EmDash",
        "Fmind.ProseBackticks",
        "Fmind.ParagraphLength",
    }
    assert [item["Line"] for item in findings if item["Check"] == "Fmind.ProseBackticks"] == [5]

    clean = tmp_path / "clean.md"
    clean.write_text(
        '---\ndescription: "Flags `--one`, `--two`, and `--three` in YAML frontmatter."\n---\n\n'
        "**Batch imports are healthy again: approve PR 418 before 17:00 UTC.**\n\n"
        "Peak memory stays below our 8 GB limit. Run ``cmd `a` `b` `c` `` once.\n\n"
        "> ```bash\n> echo `one` and `two` and `three`\n> ```\n\n"
        "````markdown\n```bash\nChecked `one` and `two` and `three` inside nested fence.\n```\n````\n",
        encoding="utf-8",
    )
    clean_run = _run_vale(vale, config, clean)
    assert clean_run.returncode == 0, clean_run.stdout + clean_run.stderr
    assert json.loads(clean_run.stdout) == {}

    html = tmp_path / "page.html"
    html.write_text(
        "<!doctype html><p>Clean outcome.</p><script>const s = `${a}` + `${b}` + `${c}`;</script>\n",
        encoding="utf-8",
    )
    html_run = _run_vale(vale, config, html)
    assert html_run.returncode == 0, html_run.stdout + html_run.stderr
    assert json.loads(html_run.stdout) == {}


def test_vale_accepts_external_starter_markdown_templates() -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for external template verification")

    config = ROOT / "dot_config/vale/dot_vale.ini"
    templates = [
        ROOT / "skills/repository-docs/templates/README.md",
        ROOT / "skills/infra-as-code/templates/README.md",
        *sorted((ROOT / "skills/documentation-site/templates").glob("*.md")),
        ROOT / "skills/python-stack/references/foundation/templates/docs-index.md",
    ]
    for path in templates:
        result = _run_vale(vale, config, path)
        assert result.returncode == 0, f"{path}: {result.stdout}{result.stderr}"
        assert json.loads(result.stdout) == {}, path
