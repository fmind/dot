#!/usr/bin/env python3
"""Validate WBS P10/P50/P90 effort estimates and compute exact Decimal commercial totals."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

TWO_PLACES = Decimal("0.01")
VALID_CATEGORIES = frozenset({"delivery", "overhead"})
MAX_LEAF_P50 = Decimal(10)
MIN_OVERHEAD_SHARE = Decimal("0.20")
MAX_UTILIZATION = Decimal("0.80")


def _quant2(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _to_decimal(raw: Any, field: str) -> Decimal:
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise ValueError(f"{field} must be a number, got {type(raw).__name__}.")
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a valid decimal number: {raw!r}") from exc
    if not value.is_finite():
        raise ValueError(f"{field} must be finite, got {raw!r}.")
    return value


def _str_d(value: Decimal) -> str:
    return f"{_quant2(value):.2f}"


def evaluate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate WBS tasks and pricing, returning exact Decimal totals and any rule violations."""
    if not isinstance(spec, dict):
        raise ValueError("Estimate spec must be a JSON object.")
    raw_tasks = spec.get("tasks")
    raw_pricing = spec.get("pricing")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("'tasks' must be a non-empty list of WBS task objects.")
    if not isinstance(raw_pricing, dict):
        raise ValueError("'pricing' must be a JSON object.")

    rate = _to_decimal(raw_pricing.get("rate"), "pricing.rate")
    if rate <= 0:
        raise ValueError("pricing.rate must be > 0.")
    raw_currency = raw_pricing.get("currency")
    currency = raw_currency.strip() if isinstance(raw_currency, str) else ""
    if not currency:
        raise ValueError("pricing.currency must be a non-empty string (for example, 'EUR' or 'USD').")
    tax_rate = _to_decimal(raw_pricing.get("tax_rate", 0), "pricing.tax_rate")
    contingency_pct = _to_decimal(raw_pricing.get("contingency_pct", 0), "pricing.contingency_pct")
    discount_pct = _to_decimal(raw_pricing.get("discount_pct", 0), "pricing.discount_pct")
    utilization = _to_decimal(raw_pricing.get("utilization", "0.80"), "pricing.utilization")
    working_days_per_year = _to_decimal(raw_pricing.get("working_days_per_year", 220), "pricing.working_days_per_year")
    if not Decimal(0) <= tax_rate <= Decimal(1):
        raise ValueError("pricing.tax_rate must be a decimal fraction between 0 and 1 (for example, 0.20 for 20%).")
    if not Decimal(0) <= contingency_pct <= Decimal(100):
        raise ValueError("pricing.contingency_pct must be between 0 and 100.")
    if not Decimal(0) <= discount_pct <= Decimal(100):
        raise ValueError("pricing.discount_pct must be between 0 and 100.")
    if not Decimal(0) < utilization <= Decimal(1):
        raise ValueError("pricing.utilization must be between 0 (exclusive) and 1 (inclusive).")
    if working_days_per_year <= 0:
        raise ValueError("pricing.working_days_per_year must be > 0.")

    violations: list[str] = []
    if utilization > MAX_UTILIZATION:
        violations.append(f"pricing.utilization ({utilization}) exceeds maximum allowed {MAX_UTILIZATION} (80%).")

    seen_ids: set[str] = set()
    phase_totals: dict[str, dict[str, Decimal]] = {}
    sum_p10 = Decimal(0)
    sum_p50 = Decimal(0)
    sum_p90 = Decimal(0)
    delivery_p50 = Decimal(0)
    overhead_p50 = Decimal(0)
    rss_low_sq = Decimal(0)
    rss_high_sq = Decimal(0)

    for idx, entry in enumerate(raw_tasks, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"tasks[{idx}] must be a JSON object.")
        raw_id = entry.get("id")
        raw_phase = entry.get("phase")
        raw_category = entry.get("category")
        task_id = raw_id.strip() if isinstance(raw_id, str) else ""
        phase = raw_phase.strip() if isinstance(raw_phase, str) else ""
        category = (
            "delivery"
            if raw_category is None
            else (raw_category.strip().lower() if isinstance(raw_category, str) else str(raw_category))
        )
        if not task_id:
            raise ValueError(f"tasks[{idx}] is missing a non-empty 'id'.")
        if task_id in seen_ids:
            violations.append(f"Duplicate task id {task_id!r}.")
        seen_ids.add(task_id)
        if not phase:
            raise ValueError(f"Task {task_id!r} is missing a non-empty 'phase'.")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Task {task_id!r} has invalid category {category!r}; expected 'delivery' or 'overhead'.")

        p10 = _to_decimal(entry.get("p10"), f"task {task_id}.p10")
        p50 = _to_decimal(entry.get("p50"), f"task {task_id}.p50")
        p90 = _to_decimal(entry.get("p90"), f"task {task_id}.p90")

        if not (Decimal(0) < p10 < p50 < p90):
            violations.append(
                f"Task {task_id!r} must satisfy 0 < p10 < p50 < p90 (got p10={p10}, p50={p50}, p90={p90})."
            )
        elif (p90 - p50) < (p50 - p10):
            violations.append(
                f"Task {task_id!r} is not right-skewed: (p90 - p50)={p90 - p50} < (p50 - p10)={p50 - p10}."
            )
        if p50 > MAX_LEAF_P50:
            violations.append(
                f"Task {task_id!r} leaf p50 ({p50} days) exceeds the {MAX_LEAF_P50}-day cap; split into smaller packages."
            )

        sum_p10 += p10
        sum_p50 += p50
        sum_p90 += p90
        if category == "overhead":
            overhead_p50 += p50
        else:
            delivery_p50 += p50

        d_low = p50 - p10
        d_high = p90 - p50
        rss_low_sq += d_low * d_low
        rss_high_sq += d_high * d_high

        bucket = phase_totals.setdefault(
            phase, {"p10": Decimal(0), "p50": Decimal(0), "p90": Decimal(0), "tasks": Decimal(0)}
        )
        bucket["p10"] += p10
        bucket["p50"] += p50
        bucket["p90"] += p90
        bucket["tasks"] += 1

    overhead_share = (overhead_p50 / sum_p50) if sum_p50 > 0 else Decimal(0)
    if overhead_share < MIN_OVERHEAD_SHARE:
        violations.append(
            f"Overhead share is {_str_d(overhead_share * 100)}% ({_str_d(overhead_p50)} / {_str_d(sum_p50)} p50 days); "
            "must be >= 20.00%."
        )

    rss_p10 = sum_p50 - rss_low_sq.sqrt()
    rss_p90 = sum_p50 + rss_high_sq.sqrt()

    subtotal_excl_tax = _quant2(sum_p50 * rate)
    discount_amount = _quant2(subtotal_excl_tax * discount_pct / Decimal(100))
    net_after_discount = subtotal_excl_tax - discount_amount
    contingency_amount = _quant2(net_after_discount * contingency_pct / Decimal(100))
    total_excl_tax = subtotal_excl_tax - discount_amount + contingency_amount
    tax_amount = _quant2(total_excl_tax * tax_rate)
    total_incl_tax = total_excl_tax + tax_amount

    effective_days_p50 = _quant2(sum_p50 / utilization)
    fte_years_p50 = (effective_days_p50 / working_days_per_year).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    phases_out = [
        {
            "phase": name,
            "task_count": int(vals["tasks"]),
            "p10_days": _str_d(vals["p10"]),
            "p50_days": _str_d(vals["p50"]),
            "p90_days": _str_d(vals["p90"]),
            "p50_subtotal_excl_tax": _str_d(vals["p50"] * rate),
        }
        for name, vals in phase_totals.items()
    ]

    return {
        "ok": not violations,
        "task_count": len(raw_tasks),
        "currency": currency,
        "effort_days": {
            "linear": {
                "p10": _str_d(sum_p10),
                "p50": _str_d(sum_p50),
                "p90": _str_d(sum_p90),
            },
            "rss_combined": {
                "p10": _str_d(rss_p10),
                "p50": _str_d(sum_p50),
                "p90": _str_d(rss_p90),
            },
            "delivery_p50": _str_d(delivery_p50),
            "overhead_p50": _str_d(overhead_p50),
            "overhead_share_pct": _str_d(overhead_share * 100),
            "utilization": f"{utilization:.2f}",
            "effective_days_p50": _str_d(effective_days_p50),
            "working_days_per_year": str(working_days_per_year),
            "fte_years_p50": f"{fte_years_p50:.3f}",
        },
        "phases": phases_out,
        "pricing": {
            "rate": _str_d(rate),
            "currency": currency,
            "tax_rate": f"{tax_rate:.4f}".rstrip("0").rstrip(".") or "0",
            "discount_pct": _str_d(discount_pct),
            "contingency_pct": _str_d(contingency_pct),
            "subtotal_excl_tax": _str_d(subtotal_excl_tax),
            "discount": _str_d(discount_amount),
            "contingency": _str_d(contingency_amount),
            "total_excl_tax": _str_d(total_excl_tax),
            "tax": _str_d(tax_amount),
            "total_incl_tax": _str_d(total_incl_tax),
            "rss_p10_excl_tax": _str_d(rss_p10 * rate),
            "rss_p90_excl_tax": _str_d(rss_p90 * rate),
            "linear_p90_excl_tax": _str_d(sum_p90 * rate),
        },
        "violations": violations,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument(
        "spec",
        help=(
            "Path to JSON WBS estimate file, or '-' for stdin. Schema: "
            "{'tasks': [{'id', 'phase', 'p10', 'p50', 'p90', 'category'?: 'delivery'|'overhead'}], "
            "'pricing': {'rate', 'currency', 'tax_rate'?, 'contingency_pct'?, 'discount_pct'?, "
            "'utilization'?, 'working_days_per_year'?}}."
        ),
    )
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit structured JSON on stdout.")
    return parser


def _format_human(result: dict[str, Any]) -> str:
    effort = result["effort_days"]
    pricing = result["pricing"]
    cur = result["currency"]
    lines = [
        f"Status: {'OK' if result['ok'] else 'FAILED'} ({result['task_count']} tasks)",
        (
            f"Effort (ideal days): linear P10={effort['linear']['p10']} / P50={effort['linear']['p50']} / "
            f"P90={effort['linear']['p90']} | RSS P10={effort['rss_combined']['p10']} / P90={effort['rss_combined']['p90']}"
        ),
        (
            f"Overhead: {effort['overhead_p50']}d ({effort['overhead_share_pct']}%) | "
            f"Effective P50 at {effort['utilization']} util: {effort['effective_days_p50']}d ({effort['fte_years_p50']} FTE-yr)"
        ),
        (
            f"Pricing ({cur}, P50 base @ {pricing['rate']}/d): subtotal {pricing['subtotal_excl_tax']} - "
            f"discount {pricing['discount']} + contingency {pricing['contingency']} = "
            f"{pricing['total_excl_tax']} excl. tax | tax {pricing['tax']} -> {pricing['total_incl_tax']} incl. tax"
        ),
    ]
    if result["violations"]:
        lines.append("Violations:")
        lines.extend(f"  - {item}" for item in result["violations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        raw = sys.stdin.read() if args.spec == "-" else Path(args.spec).read_text(encoding="utf-8")
        spec = json.loads(raw)
        result = evaluate_spec(spec)
    except (OSError, ValueError, ArithmeticError, json.JSONDecodeError) as exc:
        if args.json_output:
            sys.stderr.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.json_output:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
    else:
        sys.stdout.write(_format_human(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
