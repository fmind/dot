from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    *sorted((ROOT / ".github/workflows").glob("*.yml")),
    *sorted((ROOT / "skills/github-actions/references").glob("*.yml")),
    ROOT / "skills/cloud-run/references/deploy.yml",
]
ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
COMMENTED_ACTION = re.compile(r"^\s*(?:-\s*)?uses:\s+[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}\s+#\s+v\d[^\s]*\s*$")


def _walk(value: object) -> Iterator[object]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uses":
                yield child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_workflow_actions_are_immutable_and_version_commented() -> None:
    for path in WORKFLOWS:
        content = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(content)
        uses = [value for value in _walk(workflow) if isinstance(value, str) and not value.startswith("./")]

        assert uses, path
        assert all(ACTION.fullmatch(value) for value in uses), path
        action_lines = [line for line in content.splitlines() if re.match(r"^\s*(?:-\s*)?uses:", line)]
        assert all(COMMENTED_ACTION.fullmatch(line) for line in action_lines), path


def test_workflow_runners_are_fixed_and_sha_exception_is_absent() -> None:
    for path in WORKFLOWS:
        content = path.read_text(encoding="utf-8")
        assert "ubuntu-latest" not in content, path
        assert "runs-on: ubuntu-24.04" in content, path

    assert not (ROOT / ".github/zizmor.yml").exists()
    assert not (ROOT / "skills/github-actions/references/zizmor.yml").exists()
