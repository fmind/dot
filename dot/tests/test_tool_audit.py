from __future__ import annotations

import json
from pathlib import Path

import pytest

from dot_tasks import tool_audit as audit_tools


def test_inventory_audits_only_configured_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    active = {"version": "2.0", "install_path": "/tools/current", "source": {"type": "toml"}}
    inventory = {
        "pipx:example": [{"version": "1.0"}, active, {"version": "2.0", "source": None}],
        "npm:retired": [{"version": "1.0"}],
        "python": [{"version": "3.14", "source": {"type": "toml"}}],
    }
    monkeypatch.setattr(audit_tools, "run", lambda _command: (0, json.dumps(inventory), ""))

    assert audit_tools.installed_tools() == {"pipx:example": [active]}


@pytest.mark.parametrize("inventory", [None, [], {"pipx:example": {}}, {"npm:example": [None]}])
def test_malformed_inventory_reports_a_coverage_failure(
    inventory: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_tools, "run", lambda _command: (0, json.dumps(inventory), ""))

    assert audit_tools.main() == 2
    captured = capsys.readouterr()
    assert "mise inventory" in captured.err
    assert not captured.out


@pytest.mark.parametrize("layout", ["tool", ".mise-uv/.venv"])
def test_pip_audit_inspects_installed_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str) -> None:
    packages = tmp_path / layout / "lib/python3.14/site-packages"
    packages.mkdir(parents=True)
    commands: list[list[str]] = []

    def run(command: list[str]) -> tuple[int, str, str]:
        commands.append(command)
        return 0, json.dumps({"dependencies": [{"name": "example", "version": "1.0", "vulns": []}]}), ""

    monkeypatch.setattr(audit_tools, "run", run)
    assert audit_tools.pipx_findings("pipx:tool", tmp_path) == ([], [])
    assert commands[0][-2:] == ["--path", str(packages)]


def test_missing_pip_environment_is_a_coverage_gap(tmp_path: Path) -> None:
    assert audit_tools.pipx_findings("pipx:tool", tmp_path) == ([], ["pipx:tool: site-packages is unavailable"])


def test_trivy_finding_keeps_exact_identity_and_fix() -> None:
    report = {
        "Results": [
            {
                "Type": "pnpm",
                "Vulnerabilities": [
                    {
                        "PkgName": "nested",
                        "InstalledVersion": "1.0.0",
                        "VulnerabilityID": "GHSA-test",
                        "FixedVersion": "2.0.0",
                    }
                ],
            }
        ]
    }
    finding = audit_tools.parse_trivy_report("npm:tool", report)[0]
    assert (finding["package"], finding["version"]) == ("nested", "1.0.0")
    assert (finding["advisory"], finding["fix_available"]) == ("GHSA-test", "2.0.0")
    assert finding["dependency_chain"] == ["npm:tool", "nested"]


def test_pip_finding_keeps_exact_version_and_fix() -> None:
    report = {
        "dependencies": [{"name": "nested", "version": "1.0", "vulns": [{"id": "PYSEC-test", "fix_versions": ["1.1"]}]}]
    }
    finding = audit_tools.parse_pip_report("pipx:tool", report)[0]
    assert (finding["version"], finding["fix_available"]) == ("1.0", ["1.1"])


def test_clean_reports() -> None:
    assert audit_tools.parse_trivy_report("npm:tool", {"Results": [{"Type": "pnpm"}]}) == []
    assert audit_tools.parse_pip_report("pipx:tool", {"dependencies": []}) == []


@pytest.mark.parametrize("report", [{}, {"Results": {}}, {"Results": []}, {"Results": [{"Type": "npm"}]}, []])
def test_malformed_trivy_report_fails_closed(report: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        audit_tools.parse_trivy_report("npm:tool", report)


@pytest.mark.parametrize("report", [{}, [], {"dependencies": [{"name": "skipped", "skip_reason": "unknown"}]}])
def test_malformed_pip_report_fails_closed(report: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        audit_tools.parse_pip_report("pipx:tool", report)


def test_trivy_retains_every_installed_vulnerable_version() -> None:
    report = {
        "Results": [
            {
                "Type": "pnpm",
                "Vulnerabilities": [
                    {"PkgName": "nested", "InstalledVersion": "1.0", "VulnerabilityID": "CVE-1"},
                    {"PkgName": "nested", "InstalledVersion": "1.1", "VulnerabilityID": "CVE-1"},
                ],
            }
        ]
    }
    findings = audit_tools.parse_trivy_report("npm:tool", report)
    assert [finding["version"] for finding in findings] == ["1.0", "1.1"]


def test_main_fails_when_no_tool_environment_was_audited(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_tools, "installed_tools", dict)

    assert audit_tools.main() == 2
    assert "no npm or pipx tool environment was audited" in capsys.readouterr().err
