---
name: fastapi
description: "Existing or explicitly chosen FastAPI services and generated agent scaffolds."
---

# FastAPI

Use this for an existing or explicitly chosen FastAPI service, including an [agents-cli](../../agent-frameworks/references/agents-cli/GUIDE.md) scaffold; [litestar](litestar/GUIDE.md) remains the default for new ordinary web apps.

## Workflow

1. Inspect the installed FastAPI version and generated project contract before changing the app or dependencies.
1. Choose the official framework guidance, then adapt routes, validation, dependency lifetimes, or streaming to the existing application.
1. On FastAPI 0.142+, configure the native OpenTelemetry instrumentation with `FastAPI(telemetry={...})`; do not also add `opentelemetry-instrumentation-fastapi`. The `standard` extras include the SDK and OTLP HTTP exporter, which export once `OTEL_EXPORTER_OTLP_ENDPOINT` is set: use `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` (collector port 4318), and pass `"auto_configure": False` when the application already configures exporters. [observability](../../observability/SKILL.md) owns the rest of the stack.
1. Run local request and lifespan tests and inspect the OpenAPI output when the public schema changes.

## Gotchas

- The skill is shipped within the framework source package and is discovered by the skills CLI. Installing the Python package alone does not establish host discovery.
- `fastapi[standard]` pulls `fastapi-cli[standard]`, which installs the `fastapi-cloud-cli` vendor client. Use `fastapi[standard-no-fastapi-cloud-cli]` unless that client is a deliberate choice.
- Do not convert an agents-cli FastAPI scaffold to Litestar while implementing an agent feature.
- FastAPI's automatic OTLP export supports only `http/protobuf`: with `grpc` it exports nothing and only logs a startup warning. Its exception logs include messages and stack traces; redact them in a log processor or set `logs` to `False`.

## Official Skills

Upstream: [fastapi/fastapi](https://github.com/fastapi/fastapi). Follow the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md) and select the FastAPI application guidance.

## Documentation

- [FastAPI documentation](https://fastapi.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) · [GitHub releases](https://github.com/fastapi/fastapi/releases)
