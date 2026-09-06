from __future__ import annotations

import unittest

import pytest

from fmind_dot import tool_audit as audit_tools


class AuditToolsTest(unittest.TestCase):
    def test_trivy_finding_keeps_exact_identity_and_fix(self) -> None:
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

    def test_pip_finding_keeps_exact_version_and_fix(self) -> None:
        report = {
            "dependencies": [
                {"name": "nested", "version": "1.0", "vulns": [{"id": "PYSEC-test", "fix_versions": ["1.1"]}]}
            ]
        }
        finding = audit_tools.parse_pip_report("pipx:tool", report)[0]
        assert (finding["version"], finding["fix_available"]) == ("1.0", ["1.1"])

    def test_clean_reports(self) -> None:
        assert audit_tools.parse_trivy_report("npm:tool", {"Results": [{"Type": "pnpm"}]}) == []
        assert audit_tools.parse_pip_report("pipx:tool", {"dependencies": []}) == []

    def test_malformed_and_service_error_reports_fail_closed(self) -> None:
        for report in [{}, {"Results": {}}, {"Results": []}, {"Results": [{"Type": "npm"}]}, []]:
            with self.subTest(report=report), pytest.raises((ValueError, TypeError)):
                audit_tools.parse_trivy_report("npm:tool", report)
        for report in [{}, [], {"dependencies": [{"name": "skipped", "skip_reason": "unknown"}]}]:
            with self.subTest(report=report), pytest.raises((ValueError, TypeError)):
                audit_tools.parse_pip_report("pipx:tool", report)

    def test_trivy_retains_every_installed_vulnerable_version(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
