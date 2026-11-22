---
name: api-design
description: "Design HTTP/RPC/SDK wire contracts: RFC 9457 errors, cursor pagination, idempotency, OpenAPI, and SemVer."
---

# API & Wire Contract Design

Design predictable HTTP/REST, RPC, webhook, and SDK wire contracts across trust boundaries before writing handlers. Pair implementation with [litestar](litestar/GUIDE.md), [pydantic](pydantic.md), and [security-and-auth](security-and-auth.md); audit changes via `fmind-review-api` ([subagent](../../subagent/SKILL.md)).

## Contract Defaults

1. **Resource grammar & HTTP semantics**: keep `GET`/`HEAD` side-effect-free and cacheable; use plural noun paths (`/v1/orders/{order_id}`), consistent casing (`snake_case` or `camelCase` across one surface), and explicit units (`_ms`, `_bytes`, `_usd_micros`, ISO-8601 UTC timestamps). Use standard `Get`/`List`/`Create`/`Update`/`Delete` semantics and explicit field masks for `PATCH`.
1. **Strict boundary schemas**: validate both inbound requests and outbound responses with typed [Pydantic](pydantic.md) models (forbid loose `dict`/`Any` and extra server-owned fields to prevent mass assignment). Bound string lengths, array sizes, and request payload sizes; generate OpenAPI/Protobuf specs from live code, never hand-maintained copies.
1. **Machine-readable errors (RFC 9457)**: never return HTTP `200` with `{"error": "..."}` or leak tracebacks/SQL in `500` bodies. Emit `application/problem+json` (`type`, `title`, `status`, `detail`, `instance` / request ID) with accurate codes: `400`/`422` validation, `401` unauthenticated, `403` unauthorized, `404` missing, `409` conflict, `429` rate-limited with `Retry-After`.
1. **Bounded pagination & async jobs**: cap every `List` endpoint with an explicit `max_page_size` and opaque cursor/page tokens (avoid drifting deep `OFFSET` queries). Bound batch arrays and return `202 Accepted` with an operation status URL (or webhook) for multi-second work.
1. **Idempotency, concurrency & webhooks**: require `Idempotency-Key` deduplication on state-creating/charging `POST`s, `ETag`/`If-Match` (or version fields) for optimistic concurrency on concurrent writes, and timestamped HMAC signatures with a tight replay window on webhooks ([security-and-auth](security-and-auth.md)).
1. **Compatibility & deprecation**: treat field renames/removals, tighter request validation, type/nullability changes, or reused Protobuf tags without `reserved` as breaking. Evolve additively, gate CI with OpenAPI/schema diff checks, and publish `Deprecation` / `Sunset` headers plus dual-read/dual-write windows before removal.

## Documentation

- [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) · [Google API Improvement Proposals (AIP)](https://google.aip.dev/) · [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- Companions: [litestar](litestar/GUIDE.md), [fastapi](fastapi.md), [api-client](api-client/GUIDE.md), [pydantic](pydantic.md), [security-and-auth](security-and-auth.md).
