from __future__ import annotations

import json
import os
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
    push_index = next(index for index, step in enumerate(steps) if "--push" in str(step.get("run", "")))
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
    image_step = next(step for step in _workflow_steps() if step.get("id") == "image")
    script = str(image_step["run"])
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        'touch "$RUNNER_TEMP/build-called"\n'
        "while [[ $# -gt 0 ]]; do\n"
        '  if [[ $1 == --metadata-file ]]; then printf \'%s\' "$BUILD_METADATA" > "$2"; break; fi\n'
        "  shift\n"
        "done\n"
        'exit "$BUILD_EXIT"\n',
        encoding="utf-8",
    )
    docker.chmod(0o755)

    digest = "sha256:" + "a" * 64
    cases = [
        (
            "success",
            json.dumps({"containerimage.digest": digest}),
            "0",
            "runtime@example.iam.gserviceaccount.com",
            True,
        ),
        (
            "failed build",
            json.dumps({"containerimage.digest": digest}),
            "7",
            "runtime@example.iam.gserviceaccount.com",
            False,
        ),
        ("missing receipt", "{}", "0", "runtime@example.iam.gserviceaccount.com", False),
        (
            "tag receipt",
            json.dumps({"containerimage.digest": "image:latest"}),
            "0",
            "runtime@example.iam.gserviceaccount.com",
            False,
        ),
        (
            "malformed digest",
            json.dumps({"containerimage.digest": "sha256:short"}),
            "0",
            "runtime@example.iam.gserviceaccount.com",
            False,
        ),
        (
            "multiple receipts",
            json.dumps({"containerimage.digest": [digest, digest]}),
            "0",
            "runtime@example.iam.gserviceaccount.com",
            False,
        ),
        ("missing runtime", json.dumps({"containerimage.digest": digest}), "0", "", False),
    ]
    for name, metadata, build_exit, runtime, expected_success in cases:
        case = tmp_path / name.replace(" ", "-")
        case.mkdir()
        output = case / "output"
        output.touch()
        env = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "BUILD_EXIT": build_exit,
            "BUILD_METADATA": metadata,
            "GCP_RUNTIME_SA": runtime,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_REF_NAME": "v1.0.0",
            "IMAGE_REPOSITORY": "europe-docker.pkg.dev/project/app/image",
            "RUNNER_TEMP": str(case),
        }

        result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], env=env, check=False)

        assert (result.returncode == 0) is expected_success, name
        assert output.read_text(encoding="utf-8") == (
            f"ref=europe-docker.pkg.dev/project/app/image@{digest}\n" if expected_success else ""
        )
        if name == "missing runtime":
            assert not (case / "build-called").exists()
