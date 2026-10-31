---
name: fastapi
description: "Existing or explicitly chosen FastAPI services and generated agent scaffolds."
---

# FastAPI

Use this for an existing or explicitly chosen FastAPI service, including an [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md) scaffold; [litestar](litestar/GUIDE.md) remains the default for new ordinary web apps.

## Workflow

1. **Use native OpenTelemetry instrumentation**: on FastAPI 0.142+, configure the native OpenTelemetry instrumentation with `FastAPI(telemetry={...})`; do not also add `opentelemetry-instrumentation-fastapi`. Install the SDK and OTLP HTTP exporter through the `opentelemetry` extra when the service avoids the `standard` extras, which also include them. From 0.143, automatic exporter setup is opt-in: set `FASTAPI_OTEL_AUTO_CONFIGURE=true` or `FastAPI(telemetry={"auto_configure": True})`, plus `OTEL_EXPORTER_OTLP_ENDPOINT`. Use `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` (collector port 4318; with `grpc` it exports nothing and only logs a startup warning). Use `"auto_configure": False` when the application owns its exporters. Follow the [native telemetry docs](https://fastapi.tiangolo.com/advanced/opentelemetry/) and [observability](../../python-stack/references/observability.md) for the rest of the stack.
1. **Test locally and check OpenAPI**: run local request and lifespan tests and inspect the OpenAPI output when the public schema changes. Starlette 1.2+ warns when `TestClient` runs on `httpx`, which `filterwarnings = ["error"]` turns into a test import failure, so declare `httpx2` as the test dependency unless the `standard` extras already install it.

## Gotchas

- **Read the locked release's bundled skill**: FastAPI 0.133.1+ wheels ship the official skill matched to the installed release; locate it with `uv run python -c 'from importlib.util import find_spec; from pathlib import Path; print(Path(find_spec("fastapi").origin).with_name(".agents") / "skills/fastapi/SKILL.md")'`. Installing the package does not make hosts discover it, and its `fastapi[standard]` advice yields to the cloud-client gotcha below.
- **Avoid the bundled cloud client**: `fastapi[standard]` pulls `fastapi-cli[standard]`, which installs the `fastapi-cloud-cli` vendor client. Use `fastapi[standard-no-fastapi-cloud-cli]` unless that client is a deliberate choice.
- **Keep agents-cli scaffolds on FastAPI**: do not convert an agents-cli FastAPI scaffold to Litestar while implementing an agent feature.
- **Redact exception logs**: FastAPI's native telemetry exception logs include messages and stack traces; redact them in a log processor or set `logs` to `False`.

## Official Skills

Upstream: [fastapi/fastapi](https://github.com/fastapi/fastapi). Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) and select the FastAPI application guidance.

## Documentation

- [FastAPI documentation](https://fastapi.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) · [GitHub releases](https://github.com/fastapi/fastapi/releases)
