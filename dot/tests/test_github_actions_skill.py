from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    *sorted((ROOT / ".github/workflows").glob("*.yml")),
    *sorted((ROOT / "skills/github-actions/references/ci-cd/templates").glob("*.yml")),
    ROOT / "skills/cloud-run/templates/deploy.yml",
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


@pytest.mark.parametrize(
    "relative",
    ["skills/github-actions/references/ci-cd/templates/cd.yml", "skills/cloud-run/templates/deploy.yml"],
)
def test_release_templates_gate_publishers_on_the_tagged_revision(relative: str) -> None:
    workflow = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    gate = jobs["validate"]
    assert gate.get("permissions", workflow["permissions"]) == {"contents": "read"}
    commands = [step["run"] for step in gate["steps"] if "run" in step]
    assert "mise run all" in commands
    assert any("git status --porcelain" in command and 'test -z "$status"' in command for command in commands)
    checkout = next(step for step in gate["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] >= 100
    assert "ref" not in checkout["with"]  # Checkout the triggering tag, never moving main.
    for name, job in jobs.items():
        if name == "validate":
            continue
        needs = job["needs"] if isinstance(job["needs"], list) else [job["needs"]]
        assert "validate" in needs
        assert "always(" not in job.get("if", "")
        assert not job.get("continue-on-error")


def test_container_release_promotes_only_after_digest_verification() -> None:
    path = ROOT / "skills/github-actions/references/ci-cd/templates/cd.yml"
    steps = yaml.safe_load(path.read_text())["jobs"]["deploy-python-container"]["steps"]
    build = next(step for step in steps if step.get("uses", "").startswith("docker/build-push-action@"))
    assert build["with"]["tags"].endswith(":candidate-${{ github.sha }}")
    promotion = next(index for index, step in enumerate(steps) if step.get("name") == "Promote verified image")
    required = ("Scan every platform", "Verify image signature", "Verify platform attestations")
    for name in required:
        verified = next(index for index, step in enumerate(steps) if step.get("name") == name)
        assert verified < promotion
    assert all(not step.get("continue-on-error") and "if" not in step for step in steps)


@pytest.mark.parametrize("release_tag", ["v1.2.3", "v1.2.3\nINJECTED=value", "v1/invalid", "-invalid"])
def test_registry_promotion_preserves_digest_and_rejects_invalid_tags(tmp_path: Path, release_tag: str) -> None:
    path = ROOT / "skills/github-actions/references/ci-cd/templates/cd.yml"
    steps = yaml.safe_load(path.read_text())["jobs"]["deploy-python-container"]["steps"]
    promotion = next(step for step in steps if step.get("name") == "Promote verified image")
    executable = tmp_path / "docker"
    executable.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        'Path(os.environ["CALLS"]).write_text(json.dumps(sys.argv[1:]))\n'
    )
    executable.chmod(0o755)
    calls = tmp_path / "calls.json"
    image = "ghcr.io/example/project@sha256:" + "a" * 64
    environment = {
        "PATH": f"{tmp_path}{os.pathsep}{os.defpath}",
        "CALLS": str(calls),
        "IMAGE": image,
        "IMAGE_REPOSITORY": "ghcr.io/example/project",
        "RELEASE_TAG": release_tag,
    }
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", promotion["run"]],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if release_tag != "v1.2.3":
        assert result.returncode != 0
        assert not calls.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(calls.read_text()) == [
            "buildx",
            "imagetools",
            "create",
            "--prefer-index=false",
            "--tag",
            "ghcr.io/example/project:v1.2.3",
            "--tag",
            "ghcr.io/example/project:latest",
            image,
        ]


@pytest.mark.parametrize(
    "problem",
    [
        "none",
        "missing-arm64",
        "missing-platform",
        "unexpected-platform",
        "duplicate",
        "invalid-digest",
        "arm64-scan",
        "arm64-attestation",
    ],
)
def test_every_platform_is_verified_before_index_promotion(tmp_path: Path, problem: str) -> None:
    """Run the shipped shell/Python steps against fake registry/signing boundaries."""
    workflow = yaml.safe_load((ROOT / "skills/github-actions/references/ci-cd/templates/cd.yml").read_text())
    job = workflow["jobs"]["deploy-python-container"]
    amd64, arm64, index = ["sha256:" + character * 64 for character in "abc"]
    manifests = [
        {"platform": {"os": "linux", "architecture": arch}, "digest": digest}
        for arch, digest in (("amd64", amd64), ("arm64", arm64))
    ]
    if problem == "missing-arm64":
        manifests.pop()
    elif problem == "missing-platform":
        del manifests[1]["platform"]
    elif problem == "unexpected-platform":
        manifests[1]["platform"] = {"os": "linux", "architecture": "s390x"}
    elif problem == "duplicate":
        manifests.append(manifests[0])
    elif problem == "invalid-digest":
        manifests[1]["digest"] = "sha256:bad\nINJECTED=value"
    manifests.append(
        {
            "platform": {"os": "unknown", "architecture": "unknown"},
            "digest": index,
            "annotations": {"vnd.docker.reference.type": "attestation-manifest"},
        }
    )
    (tmp_path / "registry.json").write_text(json.dumps({"manifests": manifests}))
    executable = (
        f"#!{sys.executable}\n"
        """import json, os, sys
from pathlib import Path
name, args = Path(sys.argv[0]).name, sys.argv[1:]
with Path(os.environ["CALLS"]).open("a") as stream:
    stream.write(json.dumps([name, *args]) + "\\n")
if name == "docker" and "inspect" in args:
    print(Path(os.environ["REGISTRY"]).read_text())
if name == "trivy" and "--format" not in args and args[-1].endswith(os.environ["ARM64"]) and os.environ["PROBLEM"] == "arm64-scan":
    sys.exit(1)
if name == "trivy" and "--output" in args:
    Path(args[args.index("--output") + 1]).write_text(json.dumps({"subject": args[-1]}))
if name == "cosign" and args[0] == "attest":
    assert json.loads(Path(args[args.index("--predicate") + 1]).read_text())["subject"] == args[-1]
if name == "cosign" and args[0] == "verify-attestation" and args[-1].endswith(os.environ["ARM64"]) and os.environ["PROBLEM"] == "arm64-attestation":
    sys.exit(1)
"""
    )
    for name in ("docker", "trivy", "cosign"):
        path = tmp_path / name
        path.write_text(executable)
        path.chmod(0o755)
    environment = {
        "PATH": os.pathsep.join((str(tmp_path), str(Path(sys.executable).parent), os.defpath)),
        "RUNNER_TEMP": str(tmp_path),
        "CALLS": str(tmp_path / "calls.jsonl"),
        "REGISTRY": str(tmp_path / "registry.json"),
        "PROBLEM": problem,
        "ARM64": arm64,
        "IMAGE": f"ghcr.io/example/project@{index}",
        "IMAGE_REPOSITORY": "ghcr.io/example/project",
        "PLATFORMS": job["env"]["PLATFORMS"],
        "IDENTITY": "fixture",
        "ISSUER": "fixture",
        "RELEASE_TAG": "v1.2.3",
    }
    steps = job["steps"]
    start = next(i for i, step in enumerate(steps) if step.get("name") == "Resolve platform digests")
    scripts = tmp_path / ".github/scripts"
    scripts.mkdir(parents=True)
    helper = ROOT / "skills/github-actions/references/ci-cd/templates/image-platforms.py"
    (scripts / helper.name).write_bytes(helper.read_bytes())
    for step in steps[start:]:
        result = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            break
    assert (result.returncode == 0) is (problem == "none"), result.stderr
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    promoted = [call for call in calls if call[:4] == ["docker", "buildx", "imagetools", "create"]]
    assert bool(promoted) is (problem == "none")
    if problem == "arm64-scan":
        assert not any(call[0] == "cosign" for call in calls)
    if problem == "none":
        assert promoted[0][-1] == environment["IMAGE"]
        for prefix in (["trivy", "--config"], ["cosign", "attest"], ["cosign", "verify-attestation"]):
            assert {call[-1] for call in calls if call[:2] == prefix} == {
                f"ghcr.io/example/project@{amd64}",
                f"ghcr.io/example/project@{arm64}",
            }
