"""Opt-in headless agy skill trigger-routing evaluation suite (DOT_ROUTING_EVAL=1)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import fmind_dot.context_budget as cb
from repo_helpers import ROOT

SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["primary", "selected", "reason"],
    "properties": {
        "primary": {"type": ["string", "null"]},
        "selected": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
}

# Probe tuples: case id, user prompt, allowed primary skills, forbidden primary skills.
CASES: tuple[tuple[str, str, set[str | None], set[str]], ...] = (
    (
        "mcp-configure",
        "Connect the Datadog MCP server to Antigravity and verify it loads.",
        {"agent-harnesses"},
        {"agent-frameworks"},
    ),
    (
        "agentsview-session-search",
        "Search my past Antigravity coding sessions for auth changes and report daily token usage.",
        {"agent-harnesses"},
        {"dot-cli", "finops"},
    ),
    (
        "mcp-build",
        "Build a Python MCP server exposing our internal invoice API with protocol tests.",
        {"agent-frameworks"},
        {"agent-harnesses"},
    ),
    (
        "hooks-lefthook",
        "Configure local Lefthook pre-commit Git hooks for this repository.",
        {"git-delivery"},
        {"github"},
    ),
    (
        "github-cicd",
        "Bootstrap a new GitHub repo with MIT license, Dependabot, and Actions CI/CD.",
        {"github"},
        {"git-delivery"},
    ),
    (
        "gmail-draft",
        "Draft a reply to Alice's Gmail thread summarizing the Q4 schedule slip.",
        {"draft", "humanize"},
        {"gws"},
    ),
    (
        "gmail-search",
        "Search my Gmail inbox for Q3 invoices and export the matching Drive PDFs.",
        {"gws"},
        {"draft"},
    ),
    (
        "pep723-script",
        "Write a standalone PEP 723 Python script to aggregate JSONL application logs.",
        {"python"},
        {"extract"},
    ),
    (
        "extract-ocr",
        "Extract tables and OCR text from a scanned client PDF and XLSX spreadsheet into Markdown.",
        {"extract"},
        {"python"},
    ),
    (
        "sre-slo-migration",
        "Design multi-window burn-rate SLO alerts and an expand-contract zero-downtime DB migration.",
        {"sre"},
        {"docs"},
    ),
    (
        "docs-prd",
        "Write a feature PRD with falsifiable target metrics, guardrails, and kill criteria.",
        {"docs"},
        {"proposal", "openspec"},
    ),
    (
        "openspec-change",
        "Initialize openspec/ in this repo, propose a new change with delta specs, validate strictly, and archive it.",
        {"openspec"},
        {"docs"},
    ),
    (
        "mlops-ab-analytics",
        "Design an A/B experiment with sample-size power math, SRM check, and CUPED variance reduction.",
        {"mlops"},
        {"proposal"},
    ),
    (
        "security-compliance",
        "Assess GDPR data residency, EU AI Act risk tier, and model weight licenses for a RAG app.",
        {"code-security"},
        {"proposal"},
    ),
    (
        "finops-tco",
        "Model 12-month Cloud Run and LLM prompt-cache TCO and set billing quotas.",
        {"finops"},
        {"proposal"},
    ),
    (
        "proposal-sow",
        "Draft a consulting SOW with P10/P50/P90 WBS effort estimates and daily rates.",
        {"proposal"},
        {"finops"},
    ),
    (
        "iac-tofu",
        "Configure an OpenTofu module with GCS encrypted state, tflint, and terraform-docs.",
        {"infra-as-code"},
        {"gcloud"},
    ),
    (
        "cloud-ops-non-gcp",
        "Check our Cloudflare Worker secrets and Databricks Genie space via CLI.",
        {"cloud-ops"},
        {"gcloud"},
    ),
    (
        "clipboard-copy",
        "Copy my last handoff prompt to the system clipboard.",
        {"clipboard"},
        {"agent-harnesses"},
    ),
    (
        "negative-control",
        "What is the average and worst-case time complexity of quicksort?",
        {None},
        {"python", "docs", "full-review"},
    ),
)


def _catalog_index() -> tuple[str, set[str]]:
    lines: list[str] = []
    names: set[str] = set()
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        meta, _ = cb.parse_frontmatter(skill_md.read_text(encoding="utf-8"), str(skill_md))
        name = str(meta["name"])
        desc = str(meta["description"])
        names.add(name)
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines), names


ROUTER_AGENT = """---
name: router-probe
description: Classification-only skill router probe with zero tools.
mainAgent: true
model: inherit
excludeDefaultComponents: true
inheritCustomizations: false
inheritMcp: false
commandExecutionPolicy: "off"
tools: [finish]
---

# Skill Router Probe

Classify one user request against the provided skill catalog and immediately call `finish` with the requested JSON object.
"""


def _probe_case(
    agy_bin: str,
    schema_path: Path,
    catalog_text: str,
    workdir: Path,
    case: tuple[str, str, set[str | None], set[str]],
) -> tuple[str, dict[str, object], set[str | None], set[str]]:
    case_id, user_prompt, expected, forbidden = case
    prompt = (
        "Given ONLY the skill catalog below and the user prompt, choose the single primary skill "
        "to load first (or null if no specialized skill applies) and any secondary skills.\n\n"
        f"Available skills:\n{catalog_text}\n\n"
        f"User prompt:\n{user_prompt}\n"
    )
    proc = subprocess.run(
        [
            agy_bin,
            "--agent",
            "router-probe",
            "-p",
            prompt,
            "--model",
            os.environ.get("DOT_ROUTING_MODEL", "gemini-3.8-flash-medium"),
            "--print-timeout",
            "1m",
            "--output-format",
            "json",
            "--sandbox",
            "--disable-slash-commands",
            "--settings",
            '{"allowNonWorkspaceAccess":false}',
            "--json-schema",
            str(schema_path),
        ],
        cwd=workdir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert proc.returncode == 0, f"{case_id}: agy exited {proc.returncode}: {proc.stderr[:400]}"
    payload = json.loads(proc.stdout)
    assert payload.get("status") == "SUCCESS", f"{case_id}: bad status: {payload}"
    structured = payload.get("structured_output")
    assert isinstance(structured, dict), f"{case_id}: missing structured_output: {payload}"
    return case_id, structured, expected, forbidden


@pytest.mark.real_home
@pytest.mark.skipif(os.environ.get("DOT_ROUTING_EVAL") != "1", reason="run with DOT_ROUTING_EVAL=1")
def test_global_skill_trigger_routing_probes(tmp_path: Path) -> None:
    agy_bin = shutil.which("agy")
    assert agy_bin is not None, "agy CLI not found on PATH"
    schema_path = tmp_path / "routing.schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    workdir = tmp_path / "empty"
    agents_dir = workdir / ".agents/agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "router-probe.md").write_text(ROUTER_AGENT, encoding="utf-8")
    catalog_text, valid_names = _catalog_index()

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda c: _probe_case(agy_bin, schema_path, catalog_text, workdir, c), CASES))

    failures: list[str] = []
    for case_id, structured, expected, forbidden in results:
        primary = structured.get("primary")
        if primary is not None and primary not in valid_names:
            failures.append(f"{case_id}: invented skill {primary!r}")
        elif primary not in expected or (isinstance(primary, str) and primary in forbidden):
            failures.append(
                f"{case_id}: got primary={primary!r} selected={structured.get('selected')!r}, "
                f"expected={sorted(str(x) for x in expected)} ({structured.get('reason')})"
            )
    assert not failures, "Routing probe failures:\n" + "\n".join(failures)
