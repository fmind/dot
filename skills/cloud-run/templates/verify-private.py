"""Verify Cloud Run Invoker IAM and saved service/project IAM policy responses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def verify_private(root: Path, service_name: str) -> None:
    """Reject disabled Invoker IAM checks and every broad service/project grant."""
    service = json.loads((root / "service.json").read_text(encoding="utf-8"))
    if not isinstance(service, dict) or not isinstance(service.get("metadata"), dict):
        raise TypeError("Invalid service response")
    metadata = service["metadata"]
    annotations = metadata.get("annotations")
    if annotations is not None and not isinstance(annotations, dict):
        raise TypeError("Invalid service annotations")
    if (
        metadata["name"] != service_name
        or (annotations or {}).get("run.googleapis.com/invoker-iam-disabled", "false") != "false"
    ):
        raise SystemExit("Cloud Run Invoker IAM check is not confirmed enabled")
    for filename in ("service-iam.json", "project-iam.json"):
        policy = json.loads((root / filename).read_text(encoding="utf-8"))
        if not isinstance(policy, dict) or "error" in policy or not isinstance(policy.get("bindings", []), list):
            raise SystemExit("Invalid invocation policy response")
        for binding in policy.get("bindings", []):
            if not isinstance(binding, dict):
                raise TypeError("Invalid IAM binding")
            members = binding["members"]
            if not isinstance(members, list) or any(not isinstance(member, str) for member in members):
                raise SystemExit("Invalid IAM members")
            if {"allUsers", "allAuthenticatedUsers"}.intersection(members):
                raise SystemExit("Broad access remains in service or project IAM policy")


def main() -> None:
    """Check saved JSON responses without making cloud requests."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument(
        "responses", type=Path, help="Directory containing service.json, service-iam.json, project-iam.json"
    )
    parser.add_argument("service", help="Expected Cloud Run service name")
    args = parser.parse_args()
    try:
        verify_private(args.responses, args.service)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
        raise SystemExit("Cannot read or validate the private-invocation responses") from error
    sys.stdout.write("Invoker IAM check enabled; service and project policies contain no broad principals.\n")


if __name__ == "__main__":
    main()
