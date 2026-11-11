---
name: api-client
description: "Build typed Python HTTPX API clients with bounded pagination and retries."
---

# API Client

Prefer an existing CLI or maintained SDK when it fits; [xh](../../../xh/SKILL.md) owns ad-hoc endpoint probes and provider skills own their clients.

## Workflow

1. **Pick one HTTP stack**: reuse the project's existing client (`uv tree --invert --package httpx2` / `--package httpx`) and declare it directly; if neither is locked, add `httpx2` (Pydantic's maintained HTTPX fork). Own a single client lifetime with explicit timeouts, pool limits, and typed request/response models — skip generic SDK scaffolding for single endpoints.
1. **Bound & retry safely**: cap pages, records, response bytes, concurrency, attempts, and total deadline (read timeouts bound inactivity only); stop on repeated cursors and surface partial state; verify `URL.origin` on pagination links before following; retry only transient errors within deadline; use idempotency keys for writes and read state (or report unknown outcome) instead of blindly replaying timeouts.
1. **Verify offline first** via [httpx-tests](references/httpx-tests.md) before running authorized live calls.

## Gotchas

- **`httpx2` vs `httpx`**: `encode/httpx` stalled at `0.28.1` (2024-12); OpenAI, Anthropic, MCP, and `google-genai` 3.x use `httpx2`, whereas `google-adk`, `a2a-sdk`, Litestar, `respx`, and `pytest-httpx` still use `httpx`. Never call `httpx2.alias_httpx()` in libraries (apps may call it only before any `httpx` import).
- **OS trust store in `httpx2`**: `certifi` is not used — add CAs to host/image stores (including distroless/scratch images) or set `SSL_CERT_FILE`; never disable TLS verification.
- **Transport retries**: cover connect failures (`ConnectError`, `ConnectTimeout`) only, never HTTP status codes.
- **Stream bounds**: enforce byte caps while reading chunks and close responses/clients on cancel (`httpx2` `client.sse()` defaults `max_event_size` to 1 MiB).
- **Secrets in URLs & retry logs**: `httpx`/`httpx2` log full URLs (with query strings) at `INFO` — raise loggers to `WARNING`, pass credentials in headers, validate base URLs at config load, and never pass secrets as args to `@stamina.retry` callables (`stamina` logs call args at `WARNING`; bind on `self` or override `stamina.instrumentation.set_on_retry_hooks(...)`).
- **Deadline-aware `stamina`**: `@stamina.retry(on=predicate, attempts=N, timeout=deadline)` — return `False` for permanent errors or when `Retry-After` exceeds remaining deadline (`stamina 26.1` otherwise sleeps past `timeout`); test with `with stamina.set_testing(True, attempts=N):`.
- **Never mask errors as `[]`**: empty results mean zero records, never swallowed `403`s, truncated pages, or parse errors.
- **Untrusted or webhook URLs**: string parsing alone falls to DNS rebinding and redirects — enforce connect-time IP checks and manual redirect validation per [ssrf-egress](../../../code-security/references/code-review/references/ssrf-egress.md).

## Documentation

- [HTTPX2 clients](https://pydantic.dev/docs/httpx2/advanced/clients/) · [timeouts](https://pydantic.dev/docs/httpx2/advanced/timeouts/) · [transports](https://pydantic.dev/docs/httpx2/advanced/transports/) · [HTTPX](https://www.python-httpx.org/) · [stamina](https://stamina.hynek.me/)
- Changelogs: [HTTPX2](https://github.com/pydantic/httpx2/blob/main/src/httpx2/CHANGELOG.md) · [HTTPX](https://github.com/encode/httpx/blob/master/CHANGELOG.md) · [stamina](https://github.com/hynek/stamina/blob/main/CHANGELOG.md) · Companions: [pydantic](../pydantic.md), [python-async](../python-async/GUIDE.md), [foundation](../foundation/GUIDE.md), [gws](../../../gws/SKILL.md).
