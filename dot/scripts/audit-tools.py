#!/usr/bin/env python3
"""Audit exact npm and pipx environments installed by mise without mutating them."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any


def run(command: list[str], *, cwd: pathlib.Path | None = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, "", f"{command[0]} could not complete: {type(error).__name__}"
    return result.returncode, result.stdout, result.stderr


def installed_tools() -> dict[str, list[dict[str, Any]]]:
    code, stdout, stderr = run(["mise", "ls", "--json", "--installed"])
    if code != 0:
        raise RuntimeError(f"mise inventory failed: {stderr.strip()}")
    data = json.loads(stdout)
    if not isinstance(data, dict):
        raise TypeError("mise inventory must be an object")
    return {name: entries for name, entries in data.items() if name.startswith(("npm:", "pipx:"))}


def npm_findings(tool: str, install: pathlib.Path) -> tuple[list[dict[str, Any]], list[str]]:
    source_lock = install / "aube-lock.yaml"
    if not source_lock.is_file():
        return [], [f"{tool}: installed dependency lock is unavailable"]
    with tempfile.TemporaryDirectory(prefix="dot-tool-audit-") as directory:
        audit_root = pathlib.Path(directory)
        shutil.copyfile(source_lock, audit_root / "pnpm-lock.yaml")
        if (install / "package.json").is_file():
            shutil.copyfile(install / "package.json", audit_root / "package.json")
        code, stdout, stderr = run(["pnpm", "audit", "--lockfile-only", "--json", "--dir", str(audit_root)])
    if code not in (0, 1):
        return [], [f"{tool}: pnpm audit failed: {stderr.strip() or 'unknown operational error'}"]
    try:
        findings = parse_pnpm_report(tool, json.loads(stdout))
        if code != 0 and not findings:
            raise ValueError("audit failed without advisory details")
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return [], [f"{tool}: invalid pnpm audit report: {error}"]
    return findings, []


def parse_pnpm_report(tool: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not isinstance(report, dict) or not isinstance(report.get("advisories"), dict) or "error" in report:
        raise ValueError("expected an advisories object")
    for advisory in report["advisories"].values():
        if not advisory.get("findings"):
            raise ValueError("advisory has no installed dependency details")
        for details in advisory["findings"]:
            findings.append(
                {
                    "tool": tool,
                    "package": advisory.get("module_name"),
                    "version": details.get("version"),
                    "advisory": advisory.get("github_advisory_id") or advisory.get("url") or advisory.get("id"),
                    "fix_available": advisory.get("patched_versions", "none"),
                    "dependency_chain": details.get("paths", []),
                }
            )
    return findings


def pipx_findings(tool: str, install: pathlib.Path) -> tuple[list[dict[str, Any]], list[str]]:
    paths = sorted(install.glob("*/lib/python*/site-packages"))
    if not paths:
        return [], [f"{tool}: site-packages is unavailable"]
    command = ["pip-audit", "--format", "json", "--progress-spinner", "off", "--strict"]
    for path in paths:
        command.extend(["--path", str(path)])
    code, stdout, stderr = run(command)
    if code not in (0, 1):
        return [], [f"{tool}: pip-audit failed: {stderr.strip() or 'unknown operational error'}"]
    try:
        findings = parse_pip_report(tool, json.loads(stdout))
        if code != 0 and not findings:
            raise ValueError("audit failed without advisory details")
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return [], [f"{tool}: invalid pip-audit report: {error}"]
    return findings, []


def parse_pip_report(tool: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not isinstance(report, dict) or not isinstance(report.get("dependencies"), list):
        raise TypeError("expected a dependencies array")
    for dependency in report["dependencies"]:
        if "skip_reason" in dependency:
            raise ValueError(f"dependency {dependency.get('name', 'unknown')} was not audited")
        for vulnerability in dependency["vulns"]:
            findings.append(
                {
                    "tool": tool,
                    "package": dependency.get("name"),
                    "version": dependency.get("version"),
                    "advisory": vulnerability.get("id"),
                    "fix_available": vulnerability.get("fix_versions", []) or "none",
                    "dependency_chain": [tool, dependency.get("name")],
                }
            )
    return findings


def main() -> int:
    findings: list[dict[str, Any]] = []
    gaps: list[str] = []
    try:
        inventory = installed_tools()
    except (RuntimeError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    audited: list[dict[str, str]] = []
    for tool, entries in sorted(inventory.items()):
        if not isinstance(entries, list) or not entries:
            gaps.append(f"{tool}: missing installed versions")
            continue
        for entry in entries:
            try:
                version = entry["version"]
                install = pathlib.Path(entry["install_path"])
                label = f"{tool}@{version}"
                tool_findings, tool_gaps = (
                    npm_findings(label, install) if tool.startswith("npm:") else pipx_findings(label, install)
                )
                findings.extend(tool_findings)
                gaps.extend(tool_gaps)
                if not tool_gaps:
                    audited.append({"tool": tool, "version": version})
            except (OSError, KeyError, TypeError) as error:
                gaps.append(f"{tool}: could not inspect installation: {type(error).__name__}")
    print(json.dumps({"audited": audited, "findings": findings, "coverage_gaps": gaps}, indent=2, sort_keys=True))
    return 1 if findings or gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
