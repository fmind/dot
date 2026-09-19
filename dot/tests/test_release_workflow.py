"""Workflow privilege contracts, asserted on structure rather than on step wording."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
PINNED_ACTION_LINE = re.compile(r"^\s*(?:- )?uses: \S+@[0-9a-f]{40} # v\d+\.\d+\.\d+$")

Job = dict[str, Any]


def _jobs(path: Path) -> dict[str, Job]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]


def _writes(job: Job) -> set[str]:
    permissions = job.get("permissions", {})
    assert isinstance(permissions, dict), "use an explicit permission map, never read-all/write-all"
    return {scope for scope, access in permissions.items() if access == "write"}


def _commands(job: Job) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _index(job: Job, predicate: Any) -> int:
    matches = [index for index, step in enumerate(job["steps"]) if predicate(step)]
    assert len(matches) == 1, matches
    return matches[0]


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_workflows_default_to_read_only_pinned_bounded_jobs(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)

    assert workflow["permissions"] == {"contents": "read"}
    assert "concurrency" in workflow
    for line in content.splitlines():
        if re.match(r"^\s*(?:- )?uses:", line):
            assert PINNED_ACTION_LINE.match(line), line
    for name, job in workflow["jobs"].items():
        assert isinstance(job.get("timeout-minutes"), int), name
        for step in job["steps"]:
            if "uses" in step:
                assert PINNED_ACTION.match(step["uses"]), step["uses"]
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False, name
            # Expressions reach the shell only through env, never by interpolation.
            assert "${{" not in step.get("run", ""), (name, step.get("name"))


def test_release_credentials_never_share_a_job_with_the_build_toolchain() -> None:
    jobs = _jobs(ROOT / ".github/workflows/cd.yml")
    privileged = {name: job for name, job in jobs.items() if _writes(job)}
    unprivileged = {name: job for name, job in jobs.items() if not _writes(job)}

    assert len(privileged) == 1
    ((_, publish),) = privileged.items()
    assert _writes(publish) == {"contents", "id-token", "attestations"}
    needs = publish["needs"] if isinstance(publish["needs"], list) else [publish["needs"]]
    assert needs
    assert set(needs) <= set(unprivileged)

    # The gate, the build backend, and the complete toolchain stay beside a read-only token.
    gate = [name for name, job in unprivileged.items() if any("mise run all" in run for run in _commands(job))]
    assert gate
    assert set(gate) <= set(needs)
    for command in _commands(publish):
        assert command.startswith("mise run release:publish "), command
    for step in publish["steps"]:
        if step.get("uses", "").startswith("jdx/mise-action@"):
            assert step["with"]["cache"] is False
            assert set(step["with"]["install_args"].split()) == {"uv", "python"}


def test_release_payload_is_verified_before_it_is_attested_or_published() -> None:
    jobs = _jobs(ROOT / ".github/workflows/cd.yml")
    (publish,) = (job for job in jobs.values() if _writes(job))
    (build,) = (jobs[name] for name in ([publish["needs"]] if isinstance(publish["needs"], str) else publish["needs"]))

    gate = _index(build, lambda step: "mise run all" in step.get("run", ""))
    clean = _index(build, lambda step: "git status --porcelain" in step.get("run", ""))
    upload = _index(build, lambda step: step.get("uses", "").startswith("actions/upload-artifact@"))
    assert gate < clean < upload
    assert build["steps"][upload]["with"]["if-no-files-found"] == "error"

    download = _index(publish, lambda step: step.get("uses", "").startswith("actions/download-artifact@"))
    validate = _index(publish, lambda step: "--validate-only" in step.get("run", ""))
    attest = _index(publish, lambda step: step.get("uses", "").startswith("actions/attest@"))
    release = _index(
        publish, lambda step: "release:publish" in step.get("run", "") and "--validate-only" not in step["run"]
    )
    assert download < validate < attest < release
    assert publish["steps"][download]["with"]["name"] == build["steps"][upload]["with"]["name"]
    assert publish["steps"][download]["with"]["path"] == build["steps"][upload]["with"]["path"]
    # Only the publishing step receives the token.
    assert [index for index, step in enumerate(publish["steps"]) if "env" in step] == [release]


def test_dependabot_covers_every_directory_with_pinned_actions() -> None:
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    (actions,) = (update for update in config["updates"] if update["package-ecosystem"] == "github-actions")
    covered = {ROOT / ".github/workflows" if path == "/" else ROOT / path.strip("/") for path in actions["directories"]}
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.yml", "*.yaml"],
        cwd=ROOT,
        text=True,
        timeout=60,
    ).splitlines()
    pinned = {
        (ROOT / name).parent
        for name in tracked
        if (ROOT / name).is_file() and re.search(r"uses: \S+@[0-9a-f]{40}", (ROOT / name).read_text(encoding="utf-8"))
    }

    assert pinned
    assert pinned == covered
