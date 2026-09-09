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
    trust_index = next(index for index, step in enumerate(steps) if step["name"] == "Trust repository")
    gate_index = next(index for index, step in enumerate(steps) if step["name"] == "Run canonical gate")
    attest_index = next(index for index, step in enumerate(steps) if step["name"] == "Attest build provenance")

    assert trust_index < gate_index < attest_index
    assert steps[trust_index]["run"] == "mise trust -y mise.toml"
    assert steps[gate_index]["run"] == "mise run all"
