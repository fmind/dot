---
name: api-client
description: Build small typed Python clients for external APIs with bounded pagination and deliberate retry semantics. Use when application code must integrate an HTTP service.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/api-client
  created: "2026-09-09"
  updated: "2026-09-09"
---

# API Client

Integrate the needed API operation with a small, testable boundary. Prefer an existing CLI or maintained SDK when it satisfies the contract; [xh](../xh/SKILL.md) owns endpoint inspection and provider skills own their existing clients.

## Workflow

1. **Verify the provider contract**: inspect current primary docs and installed SDK source for API version, authentication scopes, pagination, rate limits, idempotency, error bodies, and asynchronous completion. Record unknown semantics before designing retries.
1. **Choose the seam**: reuse the project's client and sync/async model. Otherwise use HTTPX through `uv` with one owned client lifetime, explicit timeouts and pool limits, and typed request/response boundaries. Avoid a generic SDK framework for one endpoint.
1. **Bound the operation**: cap pages, records, response bytes, concurrency, attempts, and elapsed time according to configuration. HTTPX read timeouts bound inactivity, not the total duration; enforce the operation's overall deadline separately.
1. **Validate responses**: check HTTP status, expected content type, schema, and domain invariants before returning data. Preserve status/request identifiers and causes in typed errors while redacting tokens, sensitive query parameters, and bodies.
1. **Control traversal**: stop on terminal or repeated cursors, and report partial results explicitly when a limit is reached. Validate provider-returned next URLs before following them; do not send credentials to a new origin or follow redirects implicitly.
1. **Retry by meaning**: retry only documented transient failures within the total deadline. Honor valid `Retry-After`; if waiting would exceed the remaining deadline, report exhaustion instead of retrying early. Otherwise use bounded backoff with jitter. Keep authentication, permission, validation, and malformed-success failures visible.
1. **Reconcile writes**: reuse a stable provider-supported idempotency key for the same logical write. After a timeout or lost response, read authoritative operation state before retrying; without safe reconciliation or documented idempotency, return an explicit unknown outcome.
1. **Verify offline first**: exercise the [HTTPX test boundary](references/httpx-tests.md), including limits and failures; then perform only the live reads or writes authorized for this integration. Poll asynchronous jobs with a bounded deadline and verify their terminal result.

## Gotchas

- **Transport retry scope**: HTTPX transport retries cover connection errors/timeouts; they do not implement status-code retries or safe replay of an uncertain write.
- **Streaming**: enforce byte limits while reading and always close responses and clients, including cancellation paths. Checking size after buffering is not a memory bound.
- **Credential routing**: keep TLS verification enabled and make proxy/environment behavior deliberate. Validate base URLs at the configuration boundary; log only redacted endpoint identities.
- **Honest errors**: an empty list must mean no records, not a swallowed 403, exhausted page budget, or failed parse. Preserve the original exception cause without including secrets.

## Documentation

- [HTTPX clients](https://www.python-httpx.org/advanced/clients/) · [timeouts](https://www.python-httpx.org/advanced/timeouts/) · [transports](https://www.python-httpx.org/advanced/transports/)
- Companion skills: [pydantic](../pydantic/SKILL.md) (schemas), [python-stack](../python-stack/SKILL.md) (project tooling), [gws](../gws/SKILL.md) (Workspace).
