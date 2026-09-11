from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_runs_canonical_gate_before_publishing() -> None:
    path = ROOT / ".github/workflows/cd.yml"
    content = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)
    publish = workflow["jobs"]["publish"]

    permissions = publish["permissions"]
    assert "actions" not in permissions
    assert permissions["contents"] == "write"
    assert permissions["id-token"] == "write"
    assert permissions["attestations"] == "write"

    steps = publish["steps"]
    # mise-action exports MISE_TRUSTED_CONFIG_PATHS and MISE_YES, so it is what establishes trust.
    setup_index = next(index for index, step in enumerate(steps) if step["name"] == "Install toolchain")
    gate_index = next(index for index, step in enumerate(steps) if step["name"] == "Run canonical gate")
    starters_index = next(index for index, step in enumerate(steps) if step["name"] == "Run starter contracts")
    attest_index = next(index for index, step in enumerate(steps) if step["name"] == "Attest build provenance")

    assert setup_index < gate_index < starters_index < attest_index
    assert steps[setup_index]["uses"].startswith("jdx/mise-action@")
    assert steps[gate_index]["run"] == "mise run all"
    assert steps[starters_index]["run"] == "mise run test:starters"
