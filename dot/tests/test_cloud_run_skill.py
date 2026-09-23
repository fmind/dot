from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def _workflow_steps() -> list[dict[str, object]]:
    workflow = yaml.safe_load((ROOT / "skills/cloud-run/templates/deploy.yml").read_text(encoding="utf-8"))
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


@pytest.mark.parametrize("errexit", [False, True])
def test_cloud_run_build_receipt_and_runtime_identity_fail_closed(tmp_path: Path, errexit: bool) -> None:
    shell = ["bash", *(["-e"] if errexit else []), "-o", "pipefail", "-c"]
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
        validated = subprocess.run([*shell, str(inputs["run"])], env=env, check=False)
        # GitHub's default success condition prevents later steps after a failed action.
        code = validated.returncode or build_exit
        if code == 0:
            code = subprocess.run([*shell, str(image["run"])], env=env, check=False).returncode
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


@pytest.mark.parametrize(
    "problem",
    [
        "none",
        "implicit-default",
        "disabled",
        "unknown-setting",
        "wrong-service",
        "service-public",
        "project-public",
        "malformed-policy",
        "policy-read-fails",
        "conditional-custom-role",
    ],
)
def test_private_deployment_requires_both_access_postconditions(tmp_path: Path, problem: str) -> None:
    steps = _workflow_steps()
    deploy = next(
        step for step in steps if str(step.get("uses", "")).startswith("google-github-actions/deploy-cloudrun@")
    )
    assert "--invoker-iam-check" in str(deploy["with"])
    assert "--no-allow-unauthenticated" in str(deploy["with"])
    verify = next(step for step in steps if step.get("name") == "Verify private invocation")
    assert steps.index(verify) > steps.index(deploy)
    service = {"metadata": {"name": "fixture", "annotations": {"run.googleapis.com/invoker-iam-disabled": "false"}}}
    policies: dict[str, object] = {"service": {"bindings": []}, "project": {"bindings": []}}
    if problem == "implicit-default":
        service["metadata"].pop("annotations")
    elif problem in {"disabled", "unknown-setting"}:
        service["metadata"]["annotations"]["run.googleapis.com/invoker-iam-disabled"] = (
            "true" if problem == "disabled" else "unknown"
        )
    elif problem == "wrong-service":
        service["metadata"]["name"] = "other"
    elif problem in {"service-public", "project-public", "conditional-custom-role"}:
        role = "projects/fixture/roles/customInvoker" if problem == "conditional-custom-role" else "roles/run.invoker"
        policies["project" if problem == "project-public" else "service"] = {
            "bindings": [
                {
                    "role": role,
                    "members": ["allAuthenticatedUsers" if problem == "project-public" else "allUsers"],
                    "condition": {"expression": "false"},
                }
            ]
        }
    elif problem == "malformed-policy":
        policies["service"] = {"bindings": "unknown"}
    fixture = {"service": service, "policies": policies, "problem": problem}
    (tmp_path / "fixture.json").write_text(json.dumps(fixture))
    executable = tmp_path / "gcloud"
    executable.write_text(
        f"#!{sys.executable}\n"
        """import json, os, sys
from pathlib import Path
fixture = json.loads(Path(os.environ["FIXTURE"]).read_text())
if "describe" in sys.argv:
    print(json.dumps(fixture["service"]))
elif fixture["problem"] == "policy-read-fails":
    sys.exit(1)
else:
    print(json.dumps(fixture["policies"]["project" if "projects" in sys.argv else "service"]))
"""
    )
    executable.chmod(0o755)
    environment = {
        "PATH": os.pathsep.join((str(tmp_path), str(Path(sys.executable).parent), os.defpath)),
        "RUNNER_TEMP": str(tmp_path),
        "FIXTURE": str(tmp_path / "fixture.json"),
        "GCP_PROJECT": "fixture-project",
        "GCP_REGION": "europe-west1",
        "CLOUDRUN_SERVICE": "fixture",
    }
    scripts = tmp_path / ".github/scripts"
    scripts.mkdir(parents=True)
    helper = ROOT / "skills/cloud-run/templates/verify-private.py"
    (scripts / helper.name).write_bytes(helper.read_bytes())
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", str(verify["run"])],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) is (problem in {"none", "implicit-default"}), result.stderr
