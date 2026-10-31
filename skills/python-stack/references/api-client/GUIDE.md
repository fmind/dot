---
name: api-client
description: "Build typed Python HTTPX API clients with bounded pagination and retries."
---

# API Client

Integrate the needed API operation with a small, testable boundary. Prefer an existing CLI or maintained SDK when it satisfies the contract; [xh](../../../xh/SKILL.md) owns endpoint inspection and provider skills own their existing clients.

## Workflow

1. **Choose the seam**: reuse the project's client and sync/async model. Otherwise use the HTTPX package already in the lock (`uv tree --invert --package httpx2`, then `--package httpx`) and declare it directly; if neither is there, add `httpx2`, Pydantic's maintained continuation of HTTPX with the same API under `import httpx2`. Use one owned client lifetime, explicit timeouts and pool limits, and typed request/response boundaries. Avoid a generic SDK framework for one endpoint.
1. **Bound the operation**: cap pages, records, response bytes, concurrency, attempts, and elapsed time according to configuration. HTTPX read timeouts bound inactivity, not the total duration; enforce the operation's overall deadline separately.
1. **Control traversal**: stop on terminal or repeated cursors, and report partial results explicitly when a limit is reached. Validate provider-returned next URLs before following them (compare `URL.origin`); do not send credentials to a new origin or follow redirects implicitly.
1. **Retry by meaning**: retry only documented transient failures within the total deadline. Honor valid `Retry-After`; if waiting would exceed the remaining deadline, report exhaustion instead of retrying early. Otherwise use bounded backoff with jitter. Keep authentication, permission, validation, and malformed-success failures visible. Reuse the project's retry library; otherwise use `stamina`: `@stamina.retry(on=predicate, attempts=N, timeout=deadline)`, where the predicate returns False for permanent failures, True for transient ones, or the seconds from a valid `Retry-After`, and False when that wait would pass the remaining deadline (stamina 26.1 otherwise waits past `timeout`). Test with `with stamina.set_testing(True, attempts=N):`.
1. **Reconcile writes**: reuse a stable provider-supported idempotency key for the same logical write. After a timeout or lost response, read authoritative operation state before retrying; without safe reconciliation or documented idempotency, return an explicit unknown outcome.
1. **Verify offline first**: exercise the [HTTPX test boundary](references/httpx-tests.md), including limits and failures; then perform only the live reads or writes authorized for this integration. Poll asynchronous jobs with a bounded deadline and verify their terminal result.

## Gotchas

- **HTTPX and httpx2 are separate stacks**: encode/httpx has shipped no stable release since 0.28.1 (2024-12). The OpenAI, Anthropic, and MCP SDKs require `httpx2`, while the Google SDKs (google-genai, ADK, A2A), Litestar, respx, and pytest-httpx still use `httpx`. Migrating changes imports, the `httpx2` logger, and the `python-httpx2/` User-Agent. Never call `httpx2.alias_httpx()` in a library; an application calls it only before any `httpx` import.
- **httpx2 trusts the OS certificate store**: it no longer uses `certifi`; fix a TLS failure by adding the missing CA to the host or image trust store, or by pointing `SSL_CERT_FILE` at a bundle that contains it, never by disabling verification. Distroless and scratch images need CA certificates.
- **Transport retries skip status codes**: HTTPX transport retries cover only failed connects (`ConnectError`, `ConnectTimeout`); they do not implement status-code retries or safe replay of an uncertain write.
- **Bound streams while reading**: enforce byte limits while reading and always close responses and clients, including cancellation paths. Checking size after buffering is not a memory bound. For server-sent events, httpx2's `client.sse()` caps each event with `max_event_size` (1 MiB default).
- **Route credentials deliberately**: keep TLS verification enabled and make proxy/environment behavior deliberate. Validate base URLs at the configuration boundary; log only redacted endpoint identities. httpx and httpx2 log every request URL at INFO, query string included: raise those loggers to WARNING and send credentials in headers.
- **stamina logs call arguments**: its default hooks log the retried function's args and kwargs at WARNING, so never pass credentials as arguments to a retried callable; bind them in the client, or replace the hooks with `stamina.instrumentation.set_on_retry_hooks(...)`.
- **Never disguise errors as empty**: an empty list must mean no records, not a swallowed 403, exhausted page budget, or failed parse. Preserve the original exception cause without including secrets.

## Documentation

- [HTTPX2 clients](https://pydantic.dev/docs/httpx2/advanced/clients/) · [timeouts](https://pydantic.dev/docs/httpx2/advanced/timeouts/) · [transports](https://pydantic.dev/docs/httpx2/advanced/transports/) · [HTTPX](https://www.python-httpx.org/) (existing projects) · [stamina](https://stamina.hynek.me/)
- Releases: [HTTPX2 changelog](https://github.com/pydantic/httpx2/blob/main/src/httpx2/CHANGELOG.md) · [HTTPX changelog](https://github.com/encode/httpx/blob/master/CHANGELOG.md) · [stamina changelog](https://github.com/hynek/stamina/blob/main/CHANGELOG.md)
- Companion skills: [pydantic](../pydantic.md) (schemas), [python-async](../python-async/GUIDE.md) (task lifetime and cancellation), [python-stack](../foundation/GUIDE.md) (project tooling), [gws](../../../gws/SKILL.md) (Workspace).
