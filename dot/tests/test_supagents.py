"""Verify the pinned compiler and native profiles deployed by chezmoi."""

import hashlib
import json
import tomllib
from pathlib import Path

import yaml
from supagents.config import Config
from supagents.core import build, find_orphans, split_frontmatter

ROOT = Path(__file__).resolve().parents[2]


def test_supagents_vendor_integrity() -> None:
    """The artifact consumed by uv matches the recorded local candidate."""
    vendor = ROOT / "dot" / "vendor"
    provenance = json.loads((vendor / "supagents.json").read_text())
    wheel = vendor / provenance["wheel"]
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == provenance["wheel_sha256"]


def test_cross_harness_roles_are_current_and_portable(tmp_path: Path) -> None:
    """Compile outside HOME and compare every native body and managed output."""
    result = build(
        scope="project",
        config=Config.load(ROOT / "supagents.yaml"),
        source_dir=ROOT / "dot_agents" / "supagents",
        cwd=tmp_path,
    )
    assert not result.fatal_errors
    assert not result.error_count
    assert len(result.written) == 12
    assert {plan.target_name for plan in result.plans} == {"AGY", "CLAUDE", "CODEX", "COPILOT", "GROK", "OPENCODE"}
    assert {plan.source.name for plan in result.plans} == {"reviewer", "verifier"}
    assert not find_orphans(
        scope="project",
        config=Config.load(ROOT / "supagents.yaml"),
        source_dir=ROOT / "dot_agents" / "supagents",
        cwd=ROOT,
    ), "obsolete generated profiles must be removed from the chezmoi source tree"
    for plan in result.plans:
        relative = plan.output_path.relative_to(tmp_path)
        assert (ROOT / relative).read_bytes() == plan.output_path.read_bytes(), f"stale profile: {relative}"
        if plan.target_name == "CODEX":
            metadata = tomllib.loads(plan.rendered)
            body = metadata["developer_instructions"]
        else:
            frontmatter, body = split_frontmatter(plan.rendered)
            metadata = yaml.safe_load(frontmatter)
        assert metadata["name"] == plan.source.name
        assert body.strip() == plan.source.body.strip()
        assert "~/.agents/AGENTS.md" in body
        assert "Do not implement fixes or delegate further work." in body
