#!/usr/bin/env python3
"""Compute deterministic Decimal cloud + LLM monthly/annual TCO, compaction, P90 spikes, and cache breakeven."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ONE_MILLION = Decimal(1_000_000)
ONE_THOUSAND = Decimal(1_000)
CENT = Decimal("0.01")
FOUR_DP = Decimal("0.0001")
ZERO = Decimal(0)
ONE = Decimal(1)

SCHEMA_HELP = """\
JSON scenario schema:
  {
    "p90_spike_mult": "1.50",                  # optional >= 1.0 multiplier for P90 run-rate spikes
    "one_time_items": [                        # optional one-time migration/backfill spend
      {"name": "backfill", "amount": "2500"}
    ],
    "cloud_items": [                           # optional recurring infra line items
      {"name": "cloud-run", "unit_price": "100", "units": 2, "monthly_growth": "0.05"}
    ],
    "llm_workloads": [                         # optional recurring LLM workloads
      {
        "name": "agent-loop", "turns": 5, "base_input_tokens": 10000,
        "turn_growth_tokens": 5000, "output_tokens": 1000,
        "compaction_cap_tokens": 15000,        # optional per-turn input token cap
        "cache_hit_ratio": "0.80",             # omit/null for uncached; 0..1 enables write/read mults
        "cache_write_mult": "1.25", "cache_read_mult": "0.10",
        "input_per_1m": "2.00", "output_per_1m": "10.00",
        "requests_per_month": 10000, "monthly_growth": "0.00"
      }
    ]
  }
"""


def _to_decimal(value: Any, field: str, *, allow_negative: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        msg = f"{field} must be a number"
        raise ValueError(msg)
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        msg = f"{field} is not a valid decimal: {value!r}"
        raise ValueError(msg) from error
    if not parsed.is_finite():
        msg = f"{field} must be finite"
        raise ValueError(msg)
    if not allow_negative and parsed < ZERO:
        msg = f"{field} must be >= 0"
        raise ValueError(msg)
    return parsed


def _to_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        msg = f"{field} must be an integer >= {minimum}"
        raise ValueError(msg)
    return value


def _require_name(item: dict[str, Any], field: str) -> str:
    raw = item.get("name")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return raw.strip()


def _money(amount: Decimal) -> str:
    return str(amount.quantize(CENT, rounding=ROUND_HALF_UP))


def _ratio(amount: Decimal) -> str:
    return str(amount.quantize(FOUR_DP, rounding=ROUND_HALF_UP))


def _growth_factor_sum(growth: Decimal, months: int) -> Decimal:
    valid_months = _to_int(months, "months", minimum=1)
    if growth <= -ONE:
        msg = "monthly_growth must be > -1"
        raise ValueError(msg)
    total = ZERO
    factor = ONE
    for _ in range(valid_months):
        total += factor
        factor *= ONE + growth
    return total


def _session_input_tokens(
    turns: int,
    base_input_tokens: Decimal,
    turn_growth_tokens: Decimal,
    compaction_cap_tokens: Decimal | None,
) -> tuple[Decimal, Decimal]:
    uncompacted = ZERO
    compacted = ZERO
    for turn in range(turns):
        turn_tokens = base_input_tokens + Decimal(turn) * turn_growth_tokens
        uncompacted += turn_tokens
        if compaction_cap_tokens is not None and turn_tokens > compaction_cap_tokens:
            compacted += compaction_cap_tokens
        else:
            compacted += turn_tokens
    return uncompacted, compacted


def _cache_breakeven(write_mult: Decimal, read_mult: Decimal) -> tuple[Decimal | None, Decimal | None]:
    if read_mult >= ONE:
        return None, None
    if write_mult <= ONE:
        return ZERO, ZERO
    reads_per_write = (write_mult - ONE) / (ONE - read_mult)
    hit_ratio = (write_mult - ONE) / (write_mult - read_mult)
    return reads_per_write, hit_ratio


def evaluate_one_time_item(item: dict[str, Any]) -> tuple[dict[str, Any], Decimal]:
    """Evaluate one non-recurring migration or backfill line item."""
    name = _require_name(item, "one_time_items[].name")
    amount = _to_decimal(item.get("amount"), f"{name}.amount")
    return {"name": name, "amount_usd": _money(amount)}, amount


def evaluate_cloud_item(item: dict[str, Any], months: int) -> tuple[dict[str, Any], Decimal, Decimal]:
    """Evaluate one cloud line item over the requested horizon."""
    name = _require_name(item, "cloud_items[].name")
    unit_price = _to_decimal(item.get("unit_price"), f"{name}.unit_price")
    units = _to_decimal(item.get("units"), f"{name}.units")
    growth = _to_decimal(item.get("monthly_growth", 0), f"{name}.monthly_growth", allow_negative=True)
    monthly = unit_price * units
    horizon = monthly * _growth_factor_sum(growth, months)
    summary = {
        "name": name,
        "monthly_usd": _money(monthly),
        "horizon_usd": _money(horizon),
        "monthly_growth": _ratio(growth),
    }
    return summary, monthly, horizon


def evaluate_llm_workload(item: dict[str, Any], months: int) -> tuple[dict[str, Any], dict[str, Decimal]]:
    """Evaluate one LLM workload including O(T^2) compaction savings and cache breakeven."""
    name = _require_name(item, "llm_workloads[].name")
    turns = _to_int(item.get("turns", 1), f"{name}.turns", minimum=1)
    base_in = _to_decimal(item.get("base_input_tokens", 0), f"{name}.base_input_tokens")
    turn_growth = _to_decimal(item.get("turn_growth_tokens", 0), f"{name}.turn_growth_tokens")
    out_per_turn = _to_decimal(item.get("output_tokens", 0), f"{name}.output_tokens")
    raw_hit = item.get("cache_hit_ratio")
    hit_ratio: Decimal | None = None
    if raw_hit is not None:
        hit_ratio = _to_decimal(raw_hit, f"{name}.cache_hit_ratio")
        if hit_ratio > ONE:
            msg = f"{name}.cache_hit_ratio must be <= 1"
            raise ValueError(msg)
    write_mult = _to_decimal(item.get("cache_write_mult", "1.25"), f"{name}.cache_write_mult")
    read_mult = _to_decimal(item.get("cache_read_mult", "0.10"), f"{name}.cache_read_mult")
    in_price = _to_decimal(item.get("input_per_1m", 0), f"{name}.input_per_1m")
    out_price = _to_decimal(item.get("output_per_1m", 0), f"{name}.output_per_1m")
    requests = _to_decimal(item.get("requests_per_month", 0), f"{name}.requests_per_month")
    raw_cap = item.get("compaction_cap_tokens")
    cap = _to_decimal(raw_cap, f"{name}.compaction_cap_tokens") if raw_cap is not None else None
    if cap is not None and cap <= ZERO:
        msg = f"{name}.compaction_cap_tokens must be > 0 when set"
        raise ValueError(msg)
    growth = _to_decimal(item.get("monthly_growth", 0), f"{name}.monthly_growth", allow_negative=True)

    uncomp_in, comp_in = _session_input_tokens(turns, base_in, turn_growth, cap)
    session_out = Decimal(turns) * out_per_turn
    eff_input_mult = ((ONE - hit_ratio) * write_mult + hit_ratio * read_mult) if hit_ratio is not None else ONE

    def _session_cost(input_tokens: Decimal, input_mult: Decimal) -> Decimal:
        return (input_tokens * input_mult * in_price + session_out * out_price) / ONE_MILLION

    monthly_uncomp = _session_cost(uncomp_in, eff_input_mult) * requests
    monthly_comp = _session_cost(comp_in, eff_input_mult) * requests
    monthly_uncached = _session_cost(comp_in, ONE) * requests
    monthly_comp_savings = monthly_uncomp - monthly_comp
    monthly_cache_net_savings = monthly_uncached - monthly_comp

    horizon_scale = _growth_factor_sum(growth, months)
    horizon_total = monthly_comp * horizon_scale
    horizon_comp_savings = monthly_comp_savings * horizon_scale
    horizon_cache_savings = monthly_cache_net_savings * horizon_scale

    be_reads, be_ratio = _cache_breakeven(write_mult, read_mult)
    cost_per_1k = _session_cost(comp_in, eff_input_mult) * ONE_THOUSAND

    summary = {
        "name": name,
        "turns": turns,
        "cache_enabled": hit_ratio is not None,
        "uncompacted_input_tokens_per_session": str(uncomp_in.quantize(ONE, rounding=ROUND_HALF_UP)),
        "compacted_input_tokens_per_session": str(comp_in.quantize(ONE, rounding=ROUND_HALF_UP)),
        "output_tokens_per_session": str(session_out.quantize(ONE, rounding=ROUND_HALF_UP)),
        "effective_input_multiplier": _ratio(eff_input_mult),
        "cache_breakeven_reads_per_write": _ratio(be_reads) if be_reads is not None else None,
        "cache_breakeven_hit_ratio": _ratio(be_ratio) if be_ratio is not None else None,
        "cost_per_1k_requests_usd": _money(cost_per_1k),
        "monthly_uncompacted_usd": _money(monthly_uncomp),
        "monthly_compacted_usd": _money(monthly_comp),
        "monthly_compaction_savings_usd": _money(monthly_comp_savings),
        "monthly_uncached_usd": _money(monthly_uncached),
        "monthly_cache_net_savings_usd": _money(monthly_cache_net_savings),
        "horizon_usd": _money(horizon_total),
    }
    totals = {
        "monthly": monthly_comp,
        "horizon": horizon_total,
        "compaction_horizon_savings": horizon_comp_savings,
        "cache_horizon_net_savings": horizon_cache_savings,
    }
    return summary, totals


def evaluate_scenario(payload: dict[str, Any], months: int) -> dict[str, Any]:
    """Evaluate one-time items, cloud line items, and LLM workloads in a scenario mapping."""
    valid_months = _to_int(months, "months", minimum=1)
    if not isinstance(payload, dict):
        raise ValueError("Scenario root must be a JSON object")
    one_time_raw = payload.get("one_time_items", [])
    cloud_raw = payload.get("cloud_items", [])
    llm_raw = payload.get("llm_workloads", [])
    if not isinstance(one_time_raw, list) or not isinstance(cloud_raw, list) or not isinstance(llm_raw, list):
        raise ValueError("one_time_items, cloud_items, and llm_workloads must be JSON arrays")

    raw_spike = payload.get("p90_spike_mult")
    p90_spike_mult: Decimal | None = None
    if raw_spike is not None:
        p90_spike_mult = _to_decimal(raw_spike, "p90_spike_mult")
        if p90_spike_mult < ONE:
            raise ValueError("p90_spike_mult must be >= 1")

    one_time_results: list[dict[str, Any]] = []
    one_time_total = ZERO
    for raw in one_time_raw:
        if not isinstance(raw, dict):
            raise ValueError("Each one_time_items entry must be a JSON object")
        summary, amount = evaluate_one_time_item(raw)
        one_time_results.append(summary)
        one_time_total += amount

    cloud_results: list[dict[str, Any]] = []
    cloud_monthly = ZERO
    cloud_horizon = ZERO
    for raw in cloud_raw:
        if not isinstance(raw, dict):
            raise ValueError("Each cloud_items entry must be a JSON object")
        summary, monthly, horizon = evaluate_cloud_item(raw, valid_months)
        cloud_results.append(summary)
        cloud_monthly += monthly
        cloud_horizon += horizon

    llm_results: list[dict[str, Any]] = []
    llm_monthly = ZERO
    llm_horizon = ZERO
    compaction_horizon_savings = ZERO
    cache_horizon_net_savings = ZERO
    for raw in llm_raw:
        if not isinstance(raw, dict):
            raise ValueError("Each llm_workloads entry must be a JSON object")
        summary, totals = evaluate_llm_workload(raw, valid_months)
        llm_results.append(summary)
        llm_monthly += totals["monthly"]
        llm_horizon += totals["horizon"]
        compaction_horizon_savings += totals["compaction_horizon_savings"]
        cache_horizon_net_savings += totals["cache_horizon_net_savings"]

    monthly_run_rate = cloud_monthly + llm_monthly
    horizon_run_rate = cloud_horizon + llm_horizon
    horizon_total = horizon_run_rate + one_time_total

    totals_out: dict[str, Any] = {
        "one_time_total_usd": _money(one_time_total),
        "cloud_monthly_usd": _money(cloud_monthly),
        "cloud_horizon_usd": _money(cloud_horizon),
        "llm_monthly_usd": _money(llm_monthly),
        "llm_horizon_usd": _money(llm_horizon),
        "monthly_total_usd": _money(monthly_run_rate),
        "horizon_run_rate_usd": _money(horizon_run_rate),
        "horizon_total_usd": _money(horizon_total),
        "compaction_horizon_savings_usd": _money(compaction_horizon_savings),
        "cache_horizon_net_savings_usd": _money(cache_horizon_net_savings),
    }
    if p90_spike_mult is not None:
        p90_monthly = monthly_run_rate * p90_spike_mult
        p90_horizon_run_rate = horizon_run_rate * p90_spike_mult
        totals_out["p90_spike_mult"] = _ratio(p90_spike_mult)
        totals_out["p90_monthly_total_usd"] = _money(p90_monthly)
        totals_out["p90_horizon_run_rate_usd"] = _money(p90_horizon_run_rate)
        totals_out["p90_horizon_total_usd"] = _money(p90_horizon_run_rate + one_time_total)

    return {
        "months": valid_months,
        "one_time_items": one_time_results,
        "cloud_items": cloud_results,
        "llm_workloads": llm_results,
        "totals": totals_out,
    }


def _format_text(report: dict[str, Any]) -> str:
    months = report["months"]
    totals = report["totals"]
    lines = [f"FinOps TCO Summary ({months}-month horizon)"]
    if report["one_time_items"]:
        lines.append("\nOne-time line items:")
        lines.extend(f"  - {item['name']}: ${item['amount_usd']}" for item in report["one_time_items"])
    if report["cloud_items"]:
        lines.append("\nCloud line items:")
        lines.extend(
            f"  - {item['name']}: ${item['monthly_usd']}/mo | "
            f"${item['horizon_usd']}/{months}mo (growth {item['monthly_growth']})"
            for item in report["cloud_items"]
        )
    if report["llm_workloads"]:
        lines.append("\nLLM workloads:")
        for item in report["llm_workloads"]:
            be = item["cache_breakeven_hit_ratio"] or "n/a"
            lines.append(
                f"  - {item['name']} ({item['turns']}t): ${item['monthly_compacted_usd']}/mo "
                f"(${item['cost_per_1k_requests_usd']}/1k req, ${item['horizon_usd']}/{months}mo) | "
                f"compaction save ${item['monthly_compaction_savings_usd']}/mo | "
                f"cache net ${item['monthly_cache_net_savings_usd']}/mo (breakeven ratio {be})"
            )
    lines.append(
        f"\nTotals (P50): month-1 run-rate ${totals['monthly_total_usd']} | "
        f"{months}-month run-rate ${totals['horizon_run_rate_usd']} "
        f"(cloud ${totals['cloud_horizon_usd']}, llm ${totals['llm_horizon_usd']}) | "
        f"one-time ${totals['one_time_total_usd']} | total ${totals['horizon_total_usd']}"
    )
    if "p90_spike_mult" in totals:
        lines.append(
            f"P90 spike ({totals['p90_spike_mult']}x): month-1 ${totals['p90_monthly_total_usd']} | "
            f"{months}-month run-rate ${totals['p90_horizon_run_rate_usd']} | "
            f"total ${totals['p90_horizon_total_usd']}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, load JSON scenario, and print TCO output."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=SCHEMA_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument("scenario", help="Path to scenario JSON file, or '-' to read from stdin")
    parser.add_argument("--months", type=int, default=12, help="Horizon length in months (default: 12)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit structured JSON output")
    args = parser.parse_args(argv)
    if args.months < 1:
        parser.error("--months must be >= 1")
    try:
        raw_text = sys.stdin.read() if args.scenario == "-" else Path(args.scenario).read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        report = evaluate_scenario(payload, args.months)
    except (ArithmeticError, OSError, ValueError, json.JSONDecodeError) as error:
        sys.stderr.write(f"Error: {error}\n")
        return 1
    if args.as_json:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        sys.stdout.write(_format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
