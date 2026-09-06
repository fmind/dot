from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_requires_successful_ci_for_exact_tagged_commit() -> None:
    path = ROOT / ".github/workflows/cd.yml"
    content = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)
    publish = workflow["jobs"]["publish"]

    assert publish["permissions"]["actions"] == "read"
    steps = publish["steps"]
    gate_index = next(
        index for index, step in enumerate(steps) if step["name"] == "Require successful CI for tagged commit"
    )
    build_index = next(index for index, step in enumerate(steps) if step["name"] == "Build distributions")
    gate = steps[gate_index]["run"]

    assert gate_index < build_index
    assert 'git rev-parse "${GITHUB_REF_NAME}^{commit}"' in gate
    assert 'while [ "$attempt" -lt 30 ] && [ -z "$run_id" ]' in gate
    assert 'gh run list --workflow ci.yml --event push --commit "$GITHUB_SHA"' in gate
    assert 'gh run watch "$run_id" --exit-status' in gate
