"""Unit tests for the deterministic WBS commercial estimate validator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from repo_helpers import ROOT

SCRIPT = ROOT / "skills/proposal/scripts/check_estimate.py"


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _valid_spec() -> dict[str, Any]:
    return {
        "tasks": [
            {"id": "T1", "phase": "Discovery", "p10": 2, "p50": 4, "p90": 8, "category": "delivery"},
            {"id": "T2", "phase": "Build", "p10": 5, "p50": 8, "p90": 14, "category": "delivery"},
            {"id": "T3", "phase": "Governance", "p10": 2, "p50": 4, "p90": 7, "category": "overhead"},
        ],
        "pricing": {
            "rate": "1200",
            "currency": "EUR",
            "tax_rate": "0.20",
            "discount_pct": "5",
            "contingency_pct": "10",
            "utilization": "0.80",
            "working_days_per_year": 220,
        },
    }


def test_valid_wbs_from_stdin_computes_exact_decimal_totals() -> None:
    res = _run("-", "--json", stdin=json.dumps(_valid_spec()))
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["ok"] is True
    assert data["violations"] == []
    assert data["effort_days"]["linear"] == {"p10": "9.00", "p50": "16.00", "p90": "29.00"}
    assert data["effort_days"]["overhead_share_pct"] == "25.00"
    assert data["effort_days"]["effective_days_p50"] == "20.00"
    # 16 * 1200 = 19200; -5% discount = 960 -> 18240; +10% contingency = 1824 -> 20064; +20% tax = 4012.80 -> 24076.80
    assert data["pricing"]["subtotal_excl_tax"] == "19200.00"
    assert data["pricing"]["discount"] == "960.00"
    assert data["pricing"]["contingency"] == "1824.00"
    assert data["pricing"]["total_excl_tax"] == "20064.00"
    assert data["pricing"]["tax"] == "4012.80"
    assert data["pricing"]["total_incl_tax"] == "24076.80"
    # RSS P90 must be strictly smaller than linear P90 when >1 independent tasks exist.
    assert float(data["effort_days"]["rss_combined"]["p90"]) < float(data["effort_days"]["linear"]["p90"])


def test_flags_all_commercial_rule_violations(tmp_path: Path) -> None:
    bad = _valid_spec()
    bad["pricing"]["utilization"] = "0.90"
    bad["tasks"] = [
        {"id": "T1", "phase": "Build", "p10": 5, "p50": 12, "p90": 15, "category": "delivery"},
        {"id": "T1", "phase": "Ops", "p10": 1, "p50": 2, "p90": 4, "category": "overhead"},
    ]
    spec_file = tmp_path / "bad.json"
    spec_file.write_text(json.dumps(bad), encoding="utf-8")
    res = _run(str(spec_file), "--json")
    assert res.returncode == 1
    data = json.loads(res.stdout)
    assert data["ok"] is False
    joined = "\n".join(data["violations"])
    assert "exceeds maximum allowed 0.80" in joined
    assert "not right-skewed" in joined
    assert "exceeds the 10-day cap" in joined
    assert "Duplicate task id 'T1'" in joined
    assert "must be >= 20.00%" in joined


def test_help_and_malformed_json_fail_cleanly() -> None:
    assert _run("--help").returncode == 0
    bad = _run("-", "--json", stdin="{not-json")
    assert bad.returncode == 1
    assert json.loads(bad.stderr)["ok"] is False

    bad_str = _valid_spec()
    bad_str["pricing"]["currency"] = None
    res_null = _run("-", "--json", stdin=json.dumps(bad_str))
    assert res_null.returncode == 1
    assert "non-empty string" in json.loads(res_null.stderr)["error"]

    bad_huge = _valid_spec()
    bad_huge["pricing"]["rate"] = "1e30"
    res_huge = _run("-", "--json", stdin=json.dumps(bad_huge))
    assert res_huge.returncode == 1
    assert json.loads(res_huge.stderr)["ok"] is False
