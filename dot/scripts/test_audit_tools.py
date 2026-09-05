from __future__ import annotations

import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("audit-tools.py")
SPEC = importlib.util.spec_from_file_location("audit_tools", SCRIPT)
assert SPEC and SPEC.loader
audit_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_tools)


class AuditToolsTest(unittest.TestCase):
    def test_pnpm_nested_chain(self) -> None:
        report = {
            "advisories": {
                "1": {
                    "module_name": "nested",
                    "github_advisory_id": "GHSA-test",
                    "patched_versions": ">=2",
                    "findings": [{"version": "1.0.0", "paths": ["tool>parent>nested"]}],
                }
            }
        }
        self.assertEqual(
            audit_tools.parse_pnpm_report("npm:tool", report)[0]["dependency_chain"], ["tool>parent>nested"]
        )

    def test_pip_finding_keeps_exact_version_and_fix(self) -> None:
        report = {
            "dependencies": [
                {"name": "nested", "version": "1.0", "vulns": [{"id": "PYSEC-test", "fix_versions": ["1.1"]}]}
            ]
        }
        finding = audit_tools.parse_pip_report("pipx:tool", report)[0]
        self.assertEqual((finding["version"], finding["fix_available"]), ("1.0", ["1.1"]))

    def test_clean_reports(self) -> None:
        self.assertEqual(audit_tools.parse_pnpm_report("npm:tool", {"advisories": {}}), [])
        self.assertEqual(audit_tools.parse_pip_report("pipx:tool", {"dependencies": []}), [])

    def test_malformed_and_service_error_reports_fail_closed(self) -> None:
        for report in [{}, {"error": {"code": "ECONNRESET"}}, {"advisories": []}, []]:
            with self.subTest(report=report), self.assertRaises((ValueError, TypeError)):
                audit_tools.parse_pnpm_report("npm:tool", report)
        for report in [{}, [], {"dependencies": [{"name": "skipped", "skip_reason": "unknown"}]}]:
            with self.subTest(report=report), self.assertRaises((ValueError, TypeError)):
                audit_tools.parse_pip_report("pipx:tool", report)

    def test_pnpm_retains_every_installed_vulnerable_version(self) -> None:
        report = {
            "advisories": {
                "1": {
                    "module_name": "nested",
                    "findings": [{"version": "1.0", "paths": ["a>nested"]}, {"version": "1.1", "paths": ["b>nested"]}],
                }
            }
        }
        findings = audit_tools.parse_pnpm_report("npm:tool", report)
        self.assertEqual([finding["version"] for finding in findings], ["1.0", "1.1"])


if __name__ == "__main__":
    unittest.main()
