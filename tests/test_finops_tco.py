"""Unit tests for the deterministic FinOps cloud + LLM TCO script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from repo_helpers import ROOT, load_script

SCRIPT = ROOT / "skills/finops/scripts/tco_model.py"


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_evaluates_cloud_llm_compaction_and_cache_breakeven() -> None:
    scenario = {
        "cloud_items": [{"name": "cloud-run", "unit_price": "100.00", "units": 2, "monthly_growth": "0.00"}],
        "llm_workloads": [
            {
                "name": "agent-loop",
                "turns": 5,
                "base_input_tokens": 10000,
                "turn_growth_tokens": 5000,
                "output_tokens": 1000,
                "cache_hit_ratio": "0.80",
                "cache_write_mult": "1.25",
                "cache_read_mult": "0.10",
                "input_per_1m": "2.00",
                "output_per_1m": "10.00",
                "requests_per_month": 10000,
                "compaction_cap_tokens": 15000,
            }
        ],
    }
    res = _run("-", "--months", "12", "--json", stdin=json.dumps(scenario))
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["totals"]["cloud_monthly_usd"] == "200.00"
    assert data["totals"]["cloud_horizon_usd"] == "2400.00"
    llm = data["llm_workloads"][0]
    # Uncompacted 5 turns: 10k + 15k + 20k + 25k + 30k = 100,000 tokens
    # Compacted at 15k cap: 10k + 15k + 15k + 15k + 15k = 70,000 tokens
    assert llm["uncompacted_input_tokens_per_session"] == "100000"
    assert llm["compacted_input_tokens_per_session"] == "70000"
    assert llm["output_tokens_per_session"] == "5000"
    # Breakeven hit ratio for 1.25 write / 0.10 read = 0.25 / 1.15 = 0.2174
    assert llm["cache_breakeven_hit_ratio"] == "0.2174"
    assert float(llm["monthly_compaction_savings_usd"]) > 0
    assert float(llm["monthly_cache_net_savings_usd"]) > 0


def test_negative_cache_savings_when_hit_ratio_below_breakeven(tmp_path: Path) -> None:
    scenario = {
        "llm_workloads": [
            {
                "name": "cold-prefix",
                "turns": 1,
                "base_input_tokens": 100000,
                "output_tokens": 0,
                "cache_hit_ratio": "0.10",
                "cache_write_mult": "1.25",
                "cache_read_mult": "0.10",
                "input_per_1m": "10.00",
                "output_per_1m": "0",
                "requests_per_month": 1000,
            }
        ]
    }
    path = tmp_path / "cold.json"
    path.write_text(json.dumps(scenario), encoding="utf-8")
    res = _run(str(path), "--months", "1", "--json")
    assert res.returncode == 0, res.stderr
    llm = json.loads(res.stdout)["llm_workloads"][0]
    assert float(llm["monthly_cache_net_savings_usd"]) < 0


def test_help_and_invalid_inputs_fail_closed() -> None:
    help_res = _run("--help")
    assert help_res.returncode == 0
    assert "one_time_items" in help_res.stdout
    assert "p90_spike_mult" in help_res.stdout
    assert _run("-", "--months", "0", stdin="{}").returncode == 2
    bad = _run("-", stdin='{"llm_workloads": [{"name": "x", "cache_hit_ratio": "1.5"}]}')
    assert bad.returncode == 1
    assert "cache_hit_ratio" in bad.stderr
    bad_name = _run("-", stdin='{"cloud_items": [{"name": null, "unit_price": 1, "units": 1}]}')
    assert bad_name.returncode == 1
    assert "non-empty string" in bad_name.stderr
    bad_huge = _run("-", stdin='{"cloud_items": [{"name": "overflow", "unit_price": "1e30", "units": 1}]}')
    assert bad_huge.returncode == 1
    assert "Error:" in bad_huge.stderr


def test_one_time_items_p90_spike_zero_cache_hit_and_library_months_validation() -> None:
    scenario = {
        "p90_spike_mult": "1.5",
        "one_time_items": [{"name": "backfill", "amount": "500.00"}],
        "cloud_items": [{"name": "db", "unit_price": "100.00", "units": 1}],
        "llm_workloads": [
            {
                "name": "zero-hit-cache",
                "turns": 1,
                "base_input_tokens": 1_000_000,
                "output_tokens": 0,
                "cache_hit_ratio": "0",
                "cache_write_mult": "1.25",
                "cache_read_mult": "0.10",
                "input_per_1m": "10.00",
                "output_per_1m": "0",
                "requests_per_month": 1,
            }
        ],
    }
    res = _run("-", "--months", "2", "--json", stdin=json.dumps(scenario))
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # Explicit cache_hit_ratio=0 applies write penalty (1.25x): $12.50 vs $10.00 uncached -> -$2.50 net savings.
    llm = data["llm_workloads"][0]
    assert llm["cache_enabled"] is True
    assert llm["effective_input_multiplier"] == "1.2500"
    assert llm["monthly_cache_net_savings_usd"] == "-2.50"
    totals = data["totals"]
    assert totals["one_time_total_usd"] == "500.00"
    assert totals["monthly_total_usd"] == "112.50"
    assert totals["horizon_run_rate_usd"] == "225.00"
    assert totals["horizon_total_usd"] == "725.00"
    assert totals["p90_monthly_total_usd"] == "168.75"
    assert totals["p90_horizon_run_rate_usd"] == "337.50"
    assert totals["p90_horizon_total_usd"] == "837.50"

    mod = load_script("tco_model_lib", SCRIPT)
    with pytest.raises(ValueError, match="months"):
        mod.evaluate_scenario({}, 0)
