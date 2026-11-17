"""Validate canonical reviewer supagents, closed read-only host schemas, and Vale anti-slop rules."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml

from dot_tasks.skill_contracts import _read_utf8
from repo_helpers import ROOT, chezmoi, native_binary

_ROLES = (
    "agents api arch cicd cli code completeness compliance data deck design docker docs factcheck figures "
    "finops human k8s mlops perf pitch python rag readme security shell skill sql sre supagent terraform test web"
)
EXPECTED_REVIEWERS = frozenset(f"fmind-review-{r}" for r in _ROLES.split())
RETIRED_REVIEWERS = ("fmind-review-ai", "fmind-review-interface", "fmind-review-ops")
EXPECTED_AGY_TOOLS = [
    *("view_file", "list_dir", "find_by_name", "grep_search"),
    *("read_url_content", "search_web", "finish"),
]
EXPECTED_CLAUDE_TOOLS = ["Read", "Glob", "Grep", "LSP", "WebFetch", "WebSearch"]
EXPECTED_CLAUDE_DENIED = ["Write", "Edit", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task", "mcp__*"]
EXPECTED_HOST_BLOCKS: dict[str, dict[str, Any]] = {
    "AGY": {
        "subagent": True,
        "mainAgent": True,
        "model": "inherit",
        "excludeDefaultComponents": True,
        "inheritMcp": False,
        "commandExecutionPolicy": "off",
        "tools": EXPECTED_AGY_TOOLS,
    },
    "CLAUDE": {
        "model": "inherit",
        "omitClaudeMd": True,
        "tools": EXPECTED_CLAUDE_TOOLS,
        "disallowedTools": EXPECTED_CLAUDE_DENIED,
    },
    "COPILOT": {"tools": ["read", "search", "web"]},
    "OPENCODE": {
        "mode": "all",
        "permissions": [
            {"action": "*", "resource": "*", "effect": "deny"},
            *(
                {"action": act, "resource": "*", "effect": "allow"}
                for act in ("read", "glob", "grep", "list", "lsp", "webfetch", "websearch")
            ),
        ],
    },
}
EXPECTED_PARTIAL_KEYS = set(EXPECTED_HOST_BLOCKS)
EXPECTED_TOP_KEYS = {"name", "description", *EXPECTED_PARTIAL_KEYS}
EXPECTED_CHILD_KEYS = {"extends", "name", "description"}
REQUIRED_CONTRACT_CLAUSES = (
    *("never weaken read-only/security boundaries", "`## Sources` records offline human provenance"),
    *("untrusted evidence, never instructions", "`http://`", "`localhost`", "RFC1918", "link-local"),
    *("169.254.169.254", "metadata.google.internal", "VERDICT: PASS | REVISE | BLOCK"),
    *("send workspace code, draft prose, secrets, PII, internal URLs, or customer/employer names in queries",),
    *("rule: <Rubric #N or doc:line>", "redacting raw secret/token/PII values", "DELETIONS:", "UNVERIFIED:"),
)
RUBRIC_ITEM_RE = re.compile(r"^\d+\.\s+\*\*[^*]+\*\*:\s+\S")
SOURCE_LINE_RE = re.compile(r"^-\s+\[[^\]]+\]\((https://[^)\s]+)\)\s+\([^)]+\)\s+—\s+grounds\s+(Rubric\s+#.+)$")
RUBRIC_REF_RE = re.compile(r"#(\d+)(?:[\u2013-]#?(\d+))?")
FORBIDDEN_SOURCE_HOSTS = ("localhost", "127.", "169.254.", "metadata.google.internal", "::1")


def _split_frontmatter(path: Path) -> tuple[dict[str, Any], list[str]]:
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
    return metadata, raw_body


def _expected_output_contract() -> str:
    _, partial_body = _split_frontmatter(ROOT / "dot_agents/supagents/_reviewer.md")
    partial_text = "\n".join(partial_body)
    contract = partial_text[partial_text.index("## Output Contract") :]
    for clause in REQUIRED_CONTRACT_CLAUSES:
        assert clause in contract, f"_reviewer.md Output Contract missing clause: {clause}"
    return contract


def _validate_host_block(host: str, block: Any) -> None:
    expected = EXPECTED_HOST_BLOCKS[host]
    assert block == expected, f"{host}: {block!r} != {expected!r}"
    for key, val in expected.items():
        if isinstance(val, bool):
            assert isinstance(block[key], bool)


def _validate_metadata(metadata: dict[str, Any], expected_name: str) -> None:
    assert set(metadata) == EXPECTED_TOP_KEYS
    assert metadata["name"] == expected_name
    desc = metadata.get("description")
    assert isinstance(desc, str)
    assert 40 <= len(desc) <= 190
    for host in EXPECTED_PARTIAL_KEYS:
        _validate_host_block(host, metadata[host])


def _assert_domain_body_blocks(name: str, raw_body: list[str], *, compiled: bool) -> None:
    assert raw_body[:1] != []
    assert raw_body[0].startswith("# "), f"{name}: missing top-level '# ' title"
    expected_h2 = ["## Audit Rubric", "## Do Not Flag", "## Sources", *(["## Output Contract"] if compiled else [])]
    assert [ln for ln in raw_body if ln.startswith("## ")] == expected_h2, f"{name}: unexpected H2 headings"
    domain_lines = raw_body[: raw_body.index("## Output Contract")] if compiled else raw_body
    domain_text = "\n".join(domain_lines)
    assert "{{BODY}}" not in domain_text
    assert not re.search(r"\]\(\s*http://", domain_text, flags=re.IGNORECASE), f"{name}: http:// link forbidden"
    if "fmind-review-supagent" not in name:
        assert "Distills " not in domain_text, f"{name}: strip standard name-dropping"
        assert "~/.agents/DESIGN.md" not in domain_text, f"{name}: keep global rubrics workstation-independent"

    rub_idx = domain_lines.index("## Audit Rubric")
    dnf_idx = domain_lines.index("## Do Not Flag")
    src_idx = domain_lines.index("## Sources")
    cal_idxs = [i for i, ln in enumerate(domain_lines) if ln.startswith("**Calibration**:")]
    assert len(cal_idxs) == 1, f"{name}: expected one **Calibration**: line"
    assert dnf_idx < cal_idxs[0] < src_idx, f"{name}: misplaced **Calibration**:"
    assert any(ln.strip() for ln in domain_lines[1:rub_idx]), f"{name}: missing role-gate intro"

    rubric_lines = [ln for ln in domain_lines[rub_idx + 1 : dnf_idx] if ln.strip() and not ln.startswith("   ")]
    assert all(RUBRIC_ITEM_RE.match(ln) for ln in rubric_lines), f"{name}: malformed rubric item"
    assert 5 <= len(rubric_lines) <= 8, f"{name}: expected 5..8 rubric rules, got {len(rubric_lines)}"

    dnf_lines = [ln for ln in domain_lines[dnf_idx + 1 : cal_idxs[0]] if ln.strip()]
    assert 2 <= len(dnf_lines) <= 4, f"{name}: expected 2..4 Do Not Flag bullets"
    assert all(ln.startswith("- ") for ln in dnf_lines), f"{name}: bad Do Not Flag"
    assert all(sev in domain_lines[cal_idxs[0]] for sev in ("`P0`", "`P1`", "`P2`")), f"{name}: missing P0/P1/P2"

    src_lines = [ln for ln in domain_lines[src_idx + 1 :] if ln.strip()]
    assert 4 <= len(src_lines) <= 8, f"{name}: expected 4..8 sources, got {len(src_lines)}"
    covered_rules: set[int] = set()
    for ln in src_lines:
        match = SOURCE_LINE_RE.match(ln)
        assert match is not None, f"{name}: malformed source line: {ln}"
        host = (urlsplit(match.group(1)).hostname or "").lower()
        assert host != "", f"{name}: missing source host"
        assert not any(bad in host for bad in FORBIDDEN_SOURCE_HOSTS), f"{name}: unsafe source host {host}"
        for start_s, end_s in RUBRIC_REF_RE.findall(match.group(2)):
            end_n = int(end_s) if end_s else int(start_s)
            covered_rules.update(range(int(start_s), end_n + 1))
    expected_rules = set(range(1, len(rubric_lines) + 1))
    assert covered_rules == expected_rules, f"{name}: Sources cover {sorted(covered_rules)} != {sorted(expected_rules)}"


def _assert_contract_body(name: str, raw_body: list[str], expected_contract: str) -> None:
    assert 40 <= len(raw_body) <= 80, f"{name}: keep reviewer body in 40..80 lines (got {len(raw_body)})"
    assert sum(1 for ln in raw_body if ln.strip()) >= 24, f"{name}: body too thin"
    body_text = "\n".join(raw_body)
    assert len(body_text) < 10_000, f"{name}: compiled body exceeds 10,000 chars ({len(body_text)})"
    _assert_domain_body_blocks(name, raw_body, compiled=True)
    assert body_text[body_text.index("## Output Contract") :] == expected_contract, f"{name}: Output Contract drift"


def _validate_child_source(stem: str, meta: dict[str, Any], raw_body: list[str]) -> None:
    assert set(meta) == EXPECTED_CHILD_KEYS, f"{stem}: unexpected frontmatter keys {set(meta)}"
    assert meta["extends"] == "_reviewer"
    assert meta["name"] == stem
    desc = meta.get("description")
    assert isinstance(desc, str)
    assert 40 <= len(desc) <= 190
    _assert_domain_body_blocks(stem, raw_body, compiled=False)


def test_canonical_reviewer_sources_partial_and_template_stay_bounded_and_read_only() -> None:
    source_dir = ROOT / "dot_agents/supagents"
    assert sorted(p.name for p in source_dir.glob("_*")) == ["_reviewer.md"]
    partial_meta, partial_body = _split_frontmatter(source_dir / "_reviewer.md")
    assert set(partial_meta) == EXPECTED_PARTIAL_KEYS
    for host in EXPECTED_PARTIAL_KEYS:
        _validate_host_block(host, partial_meta[host])
    assert partial_body[0] == "{{BODY}}"
    expected_contract = _expected_output_contract()

    files = sorted(p for p in source_dir.glob("*.md") if not p.name.startswith("_"))
    assert {path.stem for path in files} == EXPECTED_REVIEWERS
    for path in files:
        meta, raw_body = _split_frontmatter(path)
        _validate_child_source(path.stem, meta, raw_body)

    tmeta, traw = _split_frontmatter(ROOT / "skills/subagent/templates/reviewer.md")
    _validate_metadata(tmeta, "org-review-role")
    _assert_contract_body("reviewer.md", traw, expected_contract)


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda m: m.update({"mcpServers": ["evil"]}), id="shared-mcp-servers"),
        pytest.param(lambda m: m["AGY"].update({"inheritMcp": True}), id="agy-inherit-mcp"),
        pytest.param(lambda m: m["AGY"].update({"commandExecutionPolicy": "auto"}), id="agy-cmd-auto"),
        pytest.param(lambda m: m["AGY"].update({"excludeDefaultComponents": False}), id="agy-defaults"),
        pytest.param(lambda m: m["AGY"].update({"tools": [*EXPECTED_AGY_TOOLS, "run_command"]}), id="agy-sh"),
        pytest.param(lambda m: m["CLAUDE"].update({"permissionMode": "bypassPermissions"}), id="cl-perm"),
        pytest.param(lambda m: m["CLAUDE"].update({"omitClaudeMd": False}), id="cl-creator-md"),
        pytest.param(lambda m: m["CLAUDE"].update({"maxTurns": 25}), id="cl-step-cap"),
        pytest.param(lambda m: m["CLAUDE"].update({"disallowedTools": ["Write"]}), id="cl-missing-denies"),
        pytest.param(lambda m: m["CLAUDE"].update({"tools": [*EXPECTED_CLAUDE_TOOLS, "Bash"]}), id="cl-sh"),
        pytest.param(lambda m: m["COPILOT"].update({"mcp-servers": {"x": {}}}), id="cp-mcp"),
        pytest.param(lambda m: m["COPILOT"].update({"tools": ["read", "search", "execute"]}), id="cp-exec"),
        pytest.param(lambda m: m["OPENCODE"].update({"permission": {"*": "allow"}}), id="oc-v1"),
        pytest.param(lambda m: m["OPENCODE"].update({"steps": 25}), id="oc-step-cap"),
        pytest.param(
            lambda m: m["OPENCODE"]["permissions"].append({"action": "shell", "resource": "*", "effect": "allow"}),
            id="oc-sh",
        ),
        pytest.param(
            lambda m: m["OPENCODE"]["permissions"].remove({"action": "*", "resource": "*", "effect": "deny"}),
            id="oc-missing-default-deny",
        ),
    ],
)
def test_validate_metadata_fails_closed_on_privilege_escalation(mutator: Any) -> None:
    baseline, _ = _split_frontmatter(ROOT / "skills/subagent/templates/reviewer.md")
    tampered = copy.deepcopy(baseline)
    mutator(tampered)
    with pytest.raises(AssertionError):
        _validate_metadata(tampered, str(tampered["name"]))


@pytest.mark.parametrize(
    ("meta_mutator", "body_mutator"),
    [
        pytest.param(lambda m: m.update({"AGY": {"tools": EXPECTED_AGY_TOOLS}}), None, id="child-host-override"),
        pytest.param(lambda m: m.update({"APPEND_BODY": "extra"}), None, id="child-append-body"),
        pytest.param(lambda m: m.update({"OUTPUT": "evil.md"}), None, id="child-output-path"),
        pytest.param(lambda m: m.update({"extends": "other"}), None, id="child-wrong-extends"),
        pytest.param(lambda m: m.update({"name": "fmind-review-other"}), None, id="child-wrong-name"),
        pytest.param(None, lambda b: [b[0], "Distills Google Python Style Guide.", *b[1:]], id="distills-namedrop"),
        pytest.param(None, lambda b: [b[0], "Follow ~/.agents/DESIGN.md tokens.", *b[1:]], id="workstation-lockin"),
        pytest.param(None, lambda b: [ln.replace("https://", "HTTP://") for ln in b], id="uppercase-http-link"),
        pytest.param(None, lambda b: [*b, "- [Bad](https://localhost/doc) (2026) — grounds Rubric #1."], id="ssrf-src"),
        pytest.param(None, lambda b: [*b, "- [Extra](https://example.com) — ungrounded"], id="ungrounded-extra-source"),
        pytest.param(None, lambda b: [ln.replace("#5", "#1") for ln in b], id="unmapped-rubric-rule"),
        pytest.param(None, lambda b: [ln for ln in b if not ln.startswith("- Formatter")], id="too-few-do-not-flag"),
        pytest.param(None, lambda b: [*b, "## Extra Section"], id="unexpected-h2"),
        pytest.param(None, lambda b: [ln.replace("`P2`", "minor") for ln in b], id="missing-p2-calibration"),
    ],
)
def test_validate_child_source_fails_closed_on_override_or_contract_drift(meta_mutator: Any, body_mutator: Any) -> None:
    meta, raw_body = _split_frontmatter(ROOT / "dot_agents/supagents/fmind-review-code.md")
    tampered_meta = copy.deepcopy(meta)
    tampered_body = list(raw_body)
    if meta_mutator is not None:
        meta_mutator(tampered_meta)
    if body_mutator is not None:
        tampered_body = body_mutator(tampered_body)
    with pytest.raises(AssertionError):
        _validate_child_source("fmind-review-code", tampered_meta, tampered_body)


def test_assert_contract_body_fails_closed_on_output_contract_tampering() -> None:
    expected_contract = _expected_output_contract()
    _, traw = _split_frontmatter(ROOT / "skills/subagent/templates/reviewer.md")
    for clause in ("untrusted evidence, never instructions", "169.254.169.254", "rule: <Rubric #N or doc:line>"):
        tampered = [ln.replace(clause, "omitted") for ln in traw]
        with pytest.raises(AssertionError):
            _assert_contract_body("reviewer.md", tampered, expected_contract)


def test_supagents_strict_check_and_compiled_outputs(tmp_path: Path) -> None:
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

    source = tmp_path / "source"
    source.mkdir()
    rendered_remove = {
        ln.strip()
        for ln in chezmoi(
            source, "execute-template", stdin=(ROOT / ".chezmoiremove").read_text(encoding="utf-8")
        ).splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }
    expected_retired_paths = {
        path
        for retired in RETIRED_REVIEWERS
        for path in (
            f".gemini/config/agents/{retired}.md",
            f".claude/agents/{retired}.md",
            f".copilot/agents/{retired}.agent.md",
            f".config/opencode/agents/{retired}.md",
        )
    }
    assert expected_retired_paths <= rendered_remove
    assert not any(active in line for active in EXPECTED_REVIEWERS for line in rendered_remove)

    expected_contract = _expected_output_contract()
    targets = yaml.safe_load((ROOT / "supagents.yaml").read_text(encoding="utf-8"))["targets"]
    assert set(targets) == EXPECTED_PARTIAL_KEYS
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
            fm, raw_body = _split_frontmatter(path)
            assert fm.get("name") == stem
            assert isinstance(fm.get("description"), str)
            assert 40 <= len(fm["description"]) <= 190
            _validate_host_block(host, {k: v for k, v in fm.items() if k not in {"name", "description"}})
            _assert_contract_body(f"{host}/{path.name}", raw_body, expected_contract)


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


def _run_vale(vale: Path, config: Path, target: Path, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    target_arg = str(target.relative_to(cwd)) if cwd is not None and target.is_relative_to(cwd) else str(target)
    return subprocess.run(
        [str(vale), "--no-global", "--config", str(config), "--output=JSON", target_arg],
        cwd=cwd,
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
        "In today\u2019s fast-paced landscape, we delve into a seamless rollout — a game-changer.\n\n"
        "Il convient de noter qu'on doit utiliser cette méthode afin de pouvoir avancer.\n\n"
        "Use ```inline_triple``` carefully.\n\n"
        "Checked `loader.py` and bumped `chunk_size` in `main.tf` cleanly.\n\n" + (" ".join(["word"] * 70)) + ".\n",
        encoding="utf-8",
    )
    slop_run = _run_vale(vale, config, slop)
    assert slop_run.returncode == 1, slop_run.stdout + slop_run.stderr
    findings = json.loads(slop_run.stdout)[str(slop)]
    assert {item["Check"] for item in findings} == {
        "Fmind.SlopWords",
        "Fmind.SlopStyle",
        "Fmind.Wordiness",
        "Fmind.EmDash",
        "Fmind.ProseBackticks",
        "Fmind.ParagraphLength",
        "Fmind.SentenceLength",
    }
    assert [item["Line"] for item in findings if item["Check"] == "Fmind.ProseBackticks"] == [7]
    assert {item["Severity"] for item in findings if item["Check"] in {"Fmind.SlopWords", "Fmind.EmDash"}} == {"error"}
    assert {item["Severity"] for item in findings if item["Check"] in {"Fmind.SlopStyle", "Fmind.Wordiness"}} == {
        "warning"
    }

    # Useful words like 'seamless', 'leverage', 'synergy', 'cutting-edge', and 'utilize' warn without blocking (exit code 0).
    advisory = tmp_path / "advisory.md"
    advisory.write_text(
        "We leverage seamless cutting-edge synergy in order to utilize failover; a testament to tests.\n",
        encoding="utf-8",
    )
    advisory_run = _run_vale(vale, config, advisory)
    assert advisory_run.returncode == 0, advisory_run.stdout + advisory_run.stderr
    assert {item["Check"] for item in json.loads(advisory_run.stdout)[str(advisory)]} == {
        "Fmind.SlopStyle",
        "Fmind.Wordiness",
    }

    clean = tmp_path / "clean.md"
    clean.write_text(
        '---\ndescription: "Flags `--one`, `--two`, and `--three` in YAML frontmatter."\n---\n\n'
        "<!-- Single-line note with `one`, `two`, and `three` ignored. -->\n\n"
        "<!--\n  Multi-line note with `one`, `two`, and `three` ignored.\n-->\n\n"
        "**Batch imports are healthy again: approve PR 418 before 17:00 UTC.**\n\n"
        "We deploy Unleash for feature flags, parse `<!--` literals, and track CPU utilization.\n\n"
        "Peak memory stays below our 8 GB limit. Inline `code — ok` and ``cmd `a` `b` `c` `` pass.\n\n"
        "> ```bash\n> echo `one` and `two` and `three`\n> ```\n\n"
        "````markdown\n```bash\nChecked `one` and `two` and `three` inside nested fence.\n```\n````\n",
        encoding="utf-8",
    )
    clean_run = _run_vale(vale, config, clean)
    assert clean_run.returncode == 0, clean_run.stdout + clean_run.stderr
    assert json.loads(clean_run.stdout) == {}

    # Global config allows technical backticks in README.md, docs/, and AGENTS.md while still blocking AI clichés.
    readme = tmp_path / "sub" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("Run `one`, `two`, and `three` in terminal.\n", encoding="utf-8")
    readme_run = _run_vale(vale, config, readme)
    assert readme_run.returncode == 0, readme_run.stdout + readme_run.stderr
    assert json.loads(readme_run.stdout) == {}

    docs_page = tmp_path / "docs" / "guide.md"
    docs_page.parent.mkdir(parents=True)
    docs_page.write_text("Pass `--one`, `--two`, and `--three` to the CLI.\n", encoding="utf-8")
    docs_run = _run_vale(vale, config, docs_page)
    assert docs_run.returncode == 0, docs_run.stdout + docs_run.stderr
    assert json.loads(docs_run.stdout) == {}

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("Use `one`, `two`, and `three` — keep diffs small.\n", encoding="utf-8")
    agents_run = _run_vale(vale, config, agents_md)
    assert agents_run.returncode == 0, agents_run.stdout + agents_run.stderr
    assert json.loads(agents_run.stdout) == {}

    slop_readme = tmp_path / "README.md"
    slop_readme.write_text("Unleash the power of this tool.\n", encoding="utf-8")
    slop_readme_run = _run_vale(vale, config, slop_readme)
    assert slop_readme_run.returncode == 1, slop_readme_run.stdout + slop_readme_run.stderr
    assert [item["Check"] for item in json.loads(slop_readme_run.stdout)[str(slop_readme)]] == ["Fmind.SlopWords"]

    html = tmp_path / "page.html"
    html.write_text(
        "<!doctype html><p>Clean outcome.</p><code>&mdash;</code><script>const s = `${a}` + `${b}` + `${c}`;</script>\n",
        encoding="utf-8",
    )
    html_run = _run_vale(vale, config, html)
    assert html_run.returncode == 0, html_run.stdout + html_run.stderr
    assert json.loads(html_run.stdout) == {}

    bad_html = tmp_path / "bad.html"
    bad_html.write_text("<p>Update &mdash; ready now.</p>\n", encoding="utf-8")
    bad_html_run = _run_vale(vale, config, bad_html)
    assert bad_html_run.returncode == 1, bad_html_run.stdout + bad_html_run.stderr
    assert [item["Check"] for item in json.loads(bad_html_run.stdout)[str(bad_html)]] == ["Fmind.EmDash"]


def test_vale_accepts_external_starter_markdown_templates() -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for external template verification")

    config = ROOT / ".vale.ini"
    templates = [
        ROOT / "README.md",
        ROOT / "skills/humanize/templates/report.md",
        ROOT / "skills/humanize/templates/report.html",
        ROOT / "skills/repository-docs/templates/README.md",
        ROOT / "skills/infra-as-code/templates/README.md",
        *sorted((ROOT / "skills/documentation-site/templates").glob("*.md")),
        ROOT / "skills/python-stack/references/foundation/templates/docs-index.md",
    ]
    for path in templates:
        result = _run_vale(vale, config, path, cwd=ROOT)
        assert result.returncode == 0, f"{path}: {result.stdout}{result.stderr}"
        assert json.loads(result.stdout) == {}, path
