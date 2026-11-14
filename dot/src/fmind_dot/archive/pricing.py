"""Offline API equivalents; recorded provider cost remains independent."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fmind_dot.archive.usage import UsageRecord
    from fmind_dot.config import ModelPrice, PricingConfig

# Providers whose reported input is the whole prompt, with cache buckets as subsets.
CACHE_INCLUSIVE_INPUT_HARNESSES = frozenset({"codex", "grok"})
_VENDOR_PREFIXES = ("anthropic/", "google/", "openai/", "x-ai/")
_CLAUDE_DATE_SUFFIX = re.compile(r"-20\d{6}$")


def _lookup_rate(model: str, harness: str, pricing: PricingConfig) -> ModelPrice | None:
    if rate := pricing.models.get(model):
        return rate
    candidate = model
    for prefix in _VENDOR_PREFIXES:
        if candidate.startswith(prefix):
            candidate = candidate.removeprefix(prefix)
            if rate := pricing.models.get(candidate):
                return rate
            break
    # Grok Build bills turns as `<model>-build`; xAI lists only the `<model>` it serves.
    if (
        harness == "grok"
        and candidate.endswith("-build")
        and (rate := pricing.models.get(candidate.removesuffix("-build")))
    ):
        return rate
    if candidate.startswith("claude-"):
        return pricing.models.get(_CLAUDE_DATE_SUFFIX.sub("", candidate.replace(".", "-")))
    return None


def api_equivalent(record: UsageRecord, pricing: PricingConfig) -> tuple[float | None, str]:
    """Apply exact model rates to known accounting conventions only."""
    if record.measurement_kind != "provider-reported":
        return None, "measurement is not provider-reported"
    if record.harness not in {"codex", "claude", "copilot", "grok", "pi"}:
        return None, "unsupported accounting"
    if not any((record.input_tokens, record.output_tokens, record.cached_tokens, record.cache_write_tokens)):
        if record.total_tokens:
            return None, "missing token breakdown"
        if record.legacy_accounting and not (record.harness == "claude" and record.model == "<synthetic>"):
            # Earlier parsers conflated absent counters with explicit zero; the
            # normalized archive alone cannot recover that missing evidence.
            return None, "legacy zero lacks measurement evidence"
        # Current explicit zeros and Claude's local synthetic responses are known zero.
        return 0.0, ""
    rate = _lookup_rate(record.model, record.harness, pricing)
    if record.model in {"", "mixed", "unknown"} or rate is None:
        return None, "unknown or mixed model"
    # UsageRecord validation keeps 1-hour cache writes within cache writes.
    input_tokens = record.input_tokens
    if record.harness in CACHE_INCLUSIVE_INPUT_HARNESSES:
        # OpenAI input and Grok ACP input include cached reads and cache writes; Claude, Copilot, and Pi input excludes them.
        input_tokens -= record.cached_tokens + record.cache_write_tokens
        if input_tokens < 0:
            return None, f"unsupported {record.harness.capitalize()} cache accounting"
    components = (
        (input_tokens, rate.input),
        (record.output_tokens, rate.output),
        (record.cached_tokens, rate.cache_read),
        # Claude reports 1-hour writes inside its cache writes; the rest use the 5-minute rate.
        (record.cache_write_tokens - record.cache_write_1h_tokens, rate.cache_write),
        (record.cache_write_1h_tokens, rate.cache_write_1h),
    )
    if any(tokens and price is None for tokens, price in components):
        return None, "missing token rate"
    # Reasoning is a subset of output, not an additional billable bucket.
    try:
        cost = sum(tokens * price for tokens, price in components if price is not None) / 1_000_000
    except OverflowError:
        return None, "non-finite estimate"
    return (cost, "") if math.isfinite(cost) else (None, "non-finite estimate")
