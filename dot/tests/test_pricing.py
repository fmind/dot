from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fmind_dot.archive.pricing import api_equivalent
from fmind_dot.archive.store import SessionLog, ingest_session
from fmind_dot.archive.usage import UsageRecord, aggregate_usage, write_usage_record
from fmind_dot.cli import app
from fmind_dot.config import default_pricing


def record(**kwargs) -> UsageRecord:
    return UsageRecord(
        harness="codex", session_id="example", model="gpt-5.4", measurement_kind="provider-reported", **kwargs
    ).finalize()


def test_codex_cached_and_reasoning_tokens_are_not_charged_twice() -> None:
    usage = record(input_tokens=1_000_000, cached_tokens=800_000, output_tokens=100_000, reasoning_tokens=80_000)
    cost, reason = api_equivalent(usage, default_pricing())
    assert cost == pytest.approx(2.2)
    assert reason == ""
    assert usage.cost_known is False


def test_claude_cache_is_additive_and_zero_is_known() -> None:
    usage = UsageRecord(
        harness="claude",
        session_id="one",
        model="claude-sonnet-4-6",
        measurement_kind="provider-reported",
        input_tokens=1_000_000,
        cached_tokens=1_000_000,
        cache_write_tokens=1_000_000,
        output_tokens=100_000,
    ).finalize()
    assert api_equivalent(usage, default_pricing())[0] == pytest.approx(8.55)
    assert api_equivalent(record(), default_pricing()) == (0, "")


@pytest.mark.parametrize(
    "changes",
    [
        {"total_tokens": 500},
        {"model": "mixed"},
        {"model": "gpt-5.4-future"},
        {"measurement_kind": "estimated"},
        {"measurement_kind": "context-only"},
        {"extractor_version": "1"},
        {"cached_tokens": 3, "input_tokens": 2},
        {"cache_write_tokens": 1},
    ],
)
def test_unknown_accounting_is_never_free(changes: dict) -> None:
    usage = record()
    for name, value in changes.items():
        setattr(usage, name, value)
    assert api_equivalent(usage, default_pricing())[0] is None


def test_aggregate_partial_pricing_is_separate_from_recorded_cost() -> None:
    known = record(input_tokens=1_000_000, cost_usd=4, cost_known=True)
    unknown = record()
    unknown.model = "mixed"
    result = aggregate_usage([known, unknown])[0].to_dict()
    assert result["cost_usd"] == 4
    assert result["api_equivalent_usd"] == 2.5
    assert result["priced_sessions"] == 1
    assert result["pricing_complete"] is False
    assert result["unpriced_reasons"] == {"unknown or mixed model": 1}


def test_stats_cli_honors_prices_and_preserves_prompt_privacy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    ingest_session(
        "codex", "example", [SessionLog("2026-09-09T10:00:00Z", "codex", "example", "user", "SECRET PROMPT", "/work")]
    )
    usage = record(input_tokens=1_000_000, turn_count=4)
    usage.session_id = "usage-only"
    write_usage_record(usage)
    config = tmp_path / "config.yaml"
    config.write_text("agent:\n  pricing:\n    models:\n      gpt-5.4:\n        input: 7.0\n")
    runner = CliRunner()
    result = runner.invoke(app, ["--config", str(config), "agent", "stats", "--json", "--by-model"])
    assert result.exit_code == 0, result.output
    assert "SECRET PROMPT" not in result.output
    report = json.loads(result.output)
    assert report["prompts"]["prompts"] == 1
    assert report["usage"][0]["api_equivalent_usd"] == 7
    assert report["usage"][0]["turns"] == 4
    detailed = runner.invoke(app, ["--config", str(config), "agent", "usage", "stats", "--json"])
    assert json.loads(detailed.output)[0]["api_equivalent_usd"] == 7
    human = runner.invoke(app, ["agent", "stats"])
    assert human.exit_code == 0
    assert "API EQUIV (USD)" in human.output
    assert "SECRET PROMPT" not in human.output
    invalid = runner.invoke(app, ["agent", "stats", "--since", "2026-09-10", "--until", "2026-09-01"])
    assert invalid.exit_code != 0


@pytest.mark.parametrize("price", ["-1", ".inf", ".nan", "true", "'wrong'"])
def test_invalid_price_fails_through_public_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, price: str) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config = tmp_path / "config.yaml"
    config.write_text(f"agent:\n  pricing:\n    models:\n      gpt-5.4:\n        input: {price}\n")
    result = CliRunner().invoke(app, ["--config", str(config), "agent", "stats", "--json"])
    assert result.exit_code != 0


def test_missing_rates_and_non_finite_estimates_remain_unpriced() -> None:
    pricing = default_pricing()
    pricing.models["gpt-5.4"].cache_read = None
    assert api_equivalent(record(input_tokens=100, cached_tokens=50), pricing)[0] is None
    pricing.models["gpt-5.4"].input = 1e308
    assert api_equivalent(record(input_tokens=100), pricing)[0] is None
    usage = record()
    usage.harness = "future"
    assert api_equivalent(usage, pricing)[0] is None
