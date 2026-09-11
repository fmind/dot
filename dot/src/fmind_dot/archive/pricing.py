"""Offline API equivalents; recorded provider cost remains independent."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fmind_dot.archive.usage import UsageRecord
    from fmind_dot.config import PricingConfig

# Providers whose reported input is the whole prompt, with cache buckets as subsets.
CACHE_INCLUSIVE_INPUT_HARNESSES = frozenset({"codex", "grok"})


def api_equivalent(record: UsageRecord, pricing: PricingConfig) -> tuple[float | None, str]:
    """Apply exact model rates to known accounting conventions only."""
    if record.measurement_kind != "provider-reported":
        return None, "measurement is not provider-reported"
    if record.harness not in {"codex", "claude", "copilot", "grok"}:
        return None, "unsupported accounting"
    if record.total_tokens and not any(
        (record.input_tokens, record.output_tokens, record.cached_tokens, record.cache_write_tokens)
    ):
        return None, "missing token breakdown"
    rate = pricing.models.get(record.model)
    if record.model in {"", "mixed", "unknown"} or rate is None:
        return None, "unknown or mixed model"
    input_tokens = record.input_tokens
    if record.harness == "codex":
        # Codex input includes cached reads; Claude/Copilot input excludes them.
        input_tokens -= record.cached_tokens
        if input_tokens < 0 or record.cache_write_tokens:
            return None, "unsupported Codex cache accounting"
    elif record.harness == "grok":
        # Grok ACP input is the full prompt sum: both cache buckets are subsets of it.
        input_tokens -= record.cached_tokens + record.cache_write_tokens
        if input_tokens < 0:
            return None, "unsupported Grok cache accounting"
    components = (
        (input_tokens, rate.input),
        (record.output_tokens, rate.output),
        (record.cached_tokens, rate.cache_read),
        (record.cache_write_tokens, rate.cache_write),
    )
    if any(tokens and price is None for tokens, price in components):
        return None, "missing token rate"
    # Reasoning is a subset of output, not an additional billable bucket.
    try:
        cost = sum(tokens * price for tokens, price in components if price is not None) / 1_000_000
    except OverflowError:
        return None, "non-finite estimate"
    return (cost, "") if math.isfinite(cost) else (None, "non-finite estimate")
