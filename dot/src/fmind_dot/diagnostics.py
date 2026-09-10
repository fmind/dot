"""Stable machine-readable diagnostic output shared by workstation and agent checks."""

from typing import Any


def diagnostic_report(scope: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "dot.diagnostics/v1",
        "scope": scope,
        "passed": all(check["status"] != "fail" for check in checks),
        "checks": checks,
    }
