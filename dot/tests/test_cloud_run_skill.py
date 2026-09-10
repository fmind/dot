from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def _workflow_steps() -> list[dict[str, object]]:
    workflow = yaml.safe_load((ROOT / "skills/cloud-run/references/deploy.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["deploy-cloud-run"]["steps"]
    assert isinstance(steps, list)
    return steps


def test_cloud_run_installs_exact_image_tools_before_push() -> None:
    steps = _workflow_steps()
    setup_index = next(
        index for index, step in enumerate(steps) if str(step.get("uses", "")).startswith("jdx/mise-action@")
    )
    push_index = next(
        index for index, step in enumerate(steps) if str(step.get("uses", "")).startswith("docker/build-push-action@")
    )
    build = steps[push_index]
    assert isinstance(build["with"], dict)
    assert build["with"]["push"] is True
    assert "continue-on-error" not in build
    first_use_index = next(
        index for index, step in enumerate(steps) if re.search(r"\b(?:cosign|trivy)\b", str(step.get("run", "")))
    )
    setup = steps[setup_index]
    setup_inputs = setup["with"]
    assert isinstance(setup_inputs, dict)
    tool_versions = {
        name: version for line in str(setup_inputs["tool_versions"]).splitlines() for name, version in [line.split()]
    }

    assert setup_index < first_use_index < push_index
    assert set(tool_versions) == {"cosign", "trivy"}
    assert all(EXACT_VERSION.fullmatch(version) for version in tool_versions.values())

    deployment = (ROOT / "skills/cloud-run/references/deployment.md").read_text(encoding="utf-8")
    for name, version in tool_versions.items():
        assert f'{name} = "{version}"' in deployment
    assert deployment.index("mise install --locked cosign trivy") < deployment.index("--push")


def test_cloud_run_declares_image_tools() -> None:
    contracts = json.loads((ROOT / "skills/contracts.json").read_text(encoding="utf-8"))

    assert {"cosign", "docker", "gcloud", "trivy"} <= set(contracts["skills"]["cloud-run"])


def test_cloud_run_build_receipt_and_runtime_identity_fail_closed(tmp_path: Path) -> None:
    steps = _workflow_steps()
    inputs = next(step for step in steps if step.get("name") == "Validate deployment inputs")
    build = next(step for step in steps if step.get("id") == "build")
    image = next(step for step in steps if step.get("id") == "image")
    assert steps.index(inputs) < steps.index(build) < steps.index(image)
    assert "continue-on-error" not in build
    assert "if" not in image
    digest = "sha256:" + "a" * 64
    cases = [
        ("success", digest, 0, "runtime@example.iam.gserviceaccount.com", True),
        ("failed build", digest, 7, "runtime@example.iam.gserviceaccount.com", False),
        ("missing receipt", "", 0, "runtime@example.iam.gserviceaccount.com", False),
        ("tag receipt", "image:latest", 0, "runtime@example.iam.gserviceaccount.com", False),
        ("malformed digest", "sha256:short", 0, "runtime@example.iam.gserviceaccount.com", False),
        ("multiple receipts", json.dumps([digest, digest]), 0, "runtime@example.iam.gserviceaccount.com", False),
        ("newline injection", digest + "\nINJECTED=value", 0, "runtime@example.iam.gserviceaccount.com", False),
        ("missing runtime", digest, 0, "", False),
    ]
    for name, receipt, build_exit, runtime, expected_success in cases:
        case = tmp_path / name.replace(" ", "-")
        case.mkdir()
        output = case / "output"
        environment_file = case / "environment"
        output.touch()
        environment_file.touch()
        env = {
            "PATH": "/usr/bin:/bin",
            "DIGEST": receipt,
            "GCP_RUNTIME_SA": runtime,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_ENV": str(environment_file),
            "IMAGE_REPOSITORY": "europe-docker.pkg.dev/project/app/image",
            "RUNNER_TEMP": str(case),
        }
        validated = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", str(inputs["run"])], env=env, check=False)
        # GitHub's default success condition prevents later steps after a failed action.
        code = validated.returncode or build_exit
        if code == 0:
            code = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", str(image["run"])], env=env, check=False
            ).returncode
        assert (code == 0) is expected_success, name
        assert output.read_text() == (
            f"ref=europe-docker.pkg.dev/project/app/image@{digest}\n" if expected_success else ""
        )
        if expected_success:
            values = dict(line.split("=", 1) for line in environment_file.read_text().splitlines())
            assert values["IMAGE"] == f"europe-docker.pkg.dev/project/app/image@{digest}"
            assert values["SBOM"] == f"{case}/sbom.cdx.json"
        else:
            assert environment_file.read_text() == ""
