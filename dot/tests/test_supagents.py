"""Verify role policy that `mise run check:agents` (supagents check --strict) does not cover."""

from pathlib import Path

import yaml
from supagents.config import Config
from supagents.core import build, split_frontmatter

ROOT = Path(__file__).resolve().parents[2]


def test_cross_harness_roles_keep_shared_policy_and_agy_tools(tmp_path: Path) -> None:
    """Compile outside HOME; check:agents owns warnings and generated-file drift."""
    result = build(
        scope="project",
        config=Config.load(ROOT / "supagents.yaml"),
        source_dir=ROOT / "dot_agents" / "supagents",
        cwd=tmp_path,
    )
    assert not result.fatal_errors
    assert result.plans
    for plan in result.plans:
        assert "~/.agents/AGENTS.md" in plan.source.body
        assert "this role adds a focus and defaults, not limits." in plan.source.body
        if plan.target_name == "AGY":
            frontmatter, _ = split_frontmatter(plan.rendered)
            # Antigravity grants no shell or edit tools when `tools` is omitted, and
            # `--json-schema` runs loop until timeout without `finish`.
            assert {"run_command", "replace_file_content", "finish"} <= set(yaml.safe_load(frontmatter)["tools"])
