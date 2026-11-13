---
name: fastapi
description: "Existing or explicitly chosen FastAPI services and generated agent scaffolds."
---

# FastAPI

For existing or explicitly chosen FastAPI services (including [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md) scaffolds); [litestar](litestar/GUIDE.md) is the default for new web apps.

## Workflow

1. **Native OpenTelemetry (`0.142+`)**: configure `FastAPI(telemetry={...})` instead of `opentelemetry-instrumentation-fastapi` (install `[opentelemetry]` extra if not using `standard`). From `0.143+`, auto-setup is opt-in: set `FASTAPI_OTEL_AUTO_CONFIGURE=true` or `FastAPI(telemetry={"auto_configure": True})` + `OTEL_EXPORTER_OTLP_ENDPOINT` + `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` (port `4318`; `grpc` exports nothing and warns). Set `"auto_configure": False` when the app manages exporters. See [native telemetry](https://fastapi.tiangolo.com/advanced/opentelemetry/) and [observability](../../python-stack/references/observability.md).
1. **Stream LLM and agent events cleanly**: prefer FastAPI's native `EventSourceResponse` (`from fastapi.sse import EventSourceResponse`, `0.135+`) or `StreamingResponse` with `Cache-Control: no-cache` and `X-Accel-Buffering: no`, propagating client disconnect (`await request.is_disconnected()` / `asyncio.CancelledError`) to cancel upstream model streams and enforce hard token/time bounds.
1. **Test requests, lifespan, and OpenAPI**: declare `httpx2` as a test dependency (Starlette `1.2+` warns on `httpx` in `TestClient`, failing `filterwarnings = ["error"]`).

## Gotchas

- **Bundled wheel skill (`0.133.1+`)**: read the version-matched skill via `uv run python -c 'from importlib.util import find_spec; from pathlib import Path; print(Path(find_spec("fastapi").origin).with_name(".agents") / "skills/fastapi/SKILL.md")'`.
- **Avoid `fastapi-cloud-cli`**: prefer `fastapi[standard-no-fastapi-cloud-cli]` over `fastapi[standard]` unless the vendor cloud CLI is requested.
- **Keep `agents-cli` scaffolds on FastAPI**: never rewrite them to Litestar mid-task.
- **Redact telemetry exceptions**: native telemetry logs include exception messages and tracebacks — redact via a log processor or set `logs` to `False`.

## Official Skills & Docs

Upstream: [fastapi/fastapi](https://github.com/fastapi/fastapi) (per [vendor-skills](../../agent-project/references/vendor-skills.md)). Docs: [FastAPI](https://fastapi.tiangolo.com/) · [release notes](https://fastapi.tiangolo.com/release-notes/) · [GitHub releases](https://github.com/fastapi/fastapi/releases).
