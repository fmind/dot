#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pydantic>=2.14.3"]
# ///
"""Pure-Python multi-trial evaluation harness computing pass@k and pass^k."""

import argparse
import asyncio
import json
import math
import statistics
import sys
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__version__ = "0.1.0"


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    prompt: str
    expected: str
    trials: int = Field(default=3, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrialResult(BaseModel):
    """Structured candidate output for state, trajectory, safety, and cost grading."""

    model_config = ConfigDict(extra="forbid")

    output: str
    state: dict[str, Any] = Field(default_factory=dict)
    trajectory: list[str] = Field(default_factory=list)
    forbidden_attempts: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)


class TrialOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    trial: int
    passed: bool
    latency_ms: float = Field(ge=0.0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    forbidden_attempts: int = Field(default=0, ge=0)
    error: str | None = None


def _validate_counts(n: int, c: int, k: int) -> None:
    if k <= 0 or n <= 0 or k > n:
        raise ValueError("require 1 <= k <= n")
    if c < 0 or c > n:
        raise ValueError("require 0 <= c <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Compute exact unbiased pass@k: P(at least 1 of k sampled trials passes)."""
    _validate_counts(n, c, k)
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_power_k(n: int, c: int, k: int) -> float:
    """Compute exact unbiased pass^k: P(all k sampled trials pass without replacement)."""
    _validate_counts(n, c, k)
    return 0.0 if c < k else math.comb(c, k) / math.comb(n, k)


async def evaluate_cases[R: (str, TrialResult)](
    cases: Sequence[EvalCase],
    runner: Callable[[EvalCase, int], Awaitable[R]],
    checker: Callable[[EvalCase, R], bool],
    *,
    judge: Callable[[EvalCase, R], Awaitable[bool]] | None = None,
    k: int | None = None,
    concurrency: int = 4,
    trial_timeout_s: float | None = 30.0,
) -> dict[str, object]:
    """Run paired async trials with bounded concurrency and summarize pass@k and pass^k."""
    target_k = min((case.trials for case in cases), default=1) if k is None else k
    if target_k < 1:
        raise ValueError("require k >= 1")
    if concurrency < 1:
        raise ValueError("require concurrency >= 1")
    if trial_timeout_s is not None and trial_timeout_s <= 0:
        raise ValueError("require trial_timeout_s > 0")
    seen_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids:
            raise ValueError(f"duplicate case_id: {case.case_id}")
        seen_ids.add(case.case_id)
        if case.trials < target_k:
            raise ValueError(f"case {case.case_id} has trials={case.trials} < k={target_k}")
    runner_sem = asyncio.Semaphore(concurrency)
    judge_sem = asyncio.Semaphore(concurrency)

    async def run_one(case: EvalCase, trial_index: int) -> TrialOutcome:
        loop = asyncio.get_running_loop()
        latency_ms = 0.0
        cost_usd = 0.0
        forbidden_attempts = 0
        error_name: str | None = None
        ok = False
        try:
            async with runner_sem:
                started = loop.time()
                try:
                    async with asyncio.timeout(trial_timeout_s):
                        result = await runner(case, trial_index)
                finally:
                    latency_ms = (loop.time() - started) * 1000.0
            if isinstance(result, TrialResult):
                cost_usd = result.cost_usd
                forbidden_attempts = result.forbidden_attempts
            ok = forbidden_attempts == 0 and checker(case, result)
            if ok and judge is not None:
                async with judge_sem, asyncio.timeout(trial_timeout_s):
                    ok = await judge(case, result)
        except Exception as exc:  # noqa: BLE001 - isolate trial/judge/timeout failures instead of dropping completed trials
            ok = False
            error_name = type(exc).__name__
        return TrialOutcome(
            case_id=case.case_id,
            trial=trial_index,
            passed=ok,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            forbidden_attempts=forbidden_attempts,
            error=error_name,
        )

    tasks = [run_one(case, idx) for case in cases for idx in range(case.trials)]
    outcomes = list(await asyncio.gather(*tasks))
    per_case: list[dict[str, object]] = []
    pass_at_scores: list[float] = []
    pass_power_scores: list[float] = []
    for case in cases:
        case_runs = [item for item in outcomes if item.case_id == case.case_id]
        passed_count = sum(1 for item in case_runs if item.passed)
        total = len(case_runs)
        at_k = pass_at_k(total, passed_count, target_k)
        pow_k = pass_power_k(total, passed_count, target_k)
        pass_at_scores.append(at_k)
        pass_power_scores.append(pow_k)
        per_case.append(
            {
                "case_id": case.case_id,
                "trials": total,
                "passed": passed_count,
                "errors": sum(1 for item in case_runs if item.error is not None),
                "forbidden_attempts": sum(item.forbidden_attempts for item in case_runs),
                "cost_usd": round(sum(item.cost_usd for item in case_runs), 6),
                "median_latency_ms": statistics.median(item.latency_ms for item in case_runs),
                "pass_at_k": at_k,
                "pass_power_k": pow_k,
            }
        )
    return {
        "k": target_k,
        "cases": len(per_case),
        "total_errors": sum(1 for item in outcomes if item.error is not None),
        "total_forbidden_attempts": sum(item.forbidden_attempts for item in outcomes),
        "total_cost_usd": round(sum(item.cost_usd for item in outcomes), 6),
        "mean_pass_at_k": statistics.fmean(pass_at_scores) if pass_at_scores else 0.0,
        "mean_pass_power_k": statistics.fmean(pass_power_scores) if pass_power_scores else 0.0,
        "median_latency_ms": statistics.median(o.latency_ms for o in outcomes) if outcomes else 0.0,
        "results": per_case,
    }


def _load_cases(dataset_path: Path, *, trials: int) -> list[EvalCase]:
    if trials < 1:
        raise ValueError("require trials >= 1")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("dataset must be a non-empty JSON list of cases")
    cases: list[EvalCase] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"dataset entry {idx} must be a JSON object")
        cases.append(EvalCase.model_validate({**item, "trials": item.get("trials", trials)}))
    return cases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("dataset", type=Path, help="Path to JSON dataset list of cases")
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Target k for pass@k and pass^k metrics (defaults to min case trials)",
    )
    parser.add_argument("--trials", type=int, default=3, help="Default trial count per case")
    parser.add_argument("--concurrency", type=int, default=4, help="Max concurrent runner and judge calls")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-trial timeout in seconds")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = _load_cases(args.dataset, trials=args.trials)

        async def baseline_echo(case: EvalCase, _trial: int) -> str:
            return case.expected

        summary = asyncio.run(
            evaluate_cases(
                cases,
                baseline_echo,
                lambda c, out: out.strip() == c.expected,
                k=args.k,
                concurrency=args.concurrency,
                trial_timeout_s=args.timeout,
            )
        )
    except (OSError, ValueError, ValidationError) as error:
        sys.stderr.write(f"Error: {type(error).__name__}. Check the evaluation dataset and flags.\n")
        raise SystemExit(1) from error
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
