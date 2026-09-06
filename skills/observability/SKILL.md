---
name: observability
description: Instrument a Python service or agent with JSON logs, OpenTelemetry traces and metrics, trace correlation, and GenAI spans. Use when adding logs, traces, or metrics.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/observability
  created: "2026-09-03"
  updated: "2026-09-06"
---

# Observability

Use one Python telemetry stack for services and agents: `structlog` JSON on stdout, OpenTelemetry traces and metrics over OTLP, and trace context on every related log event. Standard OTLP configuration keeps the application independent of the backend.

## Workflow

1. **Add only the Python packages in use**: `structlog`, OpenTelemetry API and SDK, the OTLP exporter, and explicit instrumentation packages for the service's HTTP framework and clients. Lock them with `uv`; avoid a vendor SDK in application code.
1. **Emit structured logs**: render one JSON object per line to stdout in production. Use `severity`, `message`, and `time` for Cloud Logging while retaining stable event names and machine-readable fields.
1. **Configure traces and metrics** through `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, and `OTEL_EXPORTER_OTLP_ENDPOINT`. A missing endpoint should leave local development quiet and should never make request handling fail.
1. **Correlate signals**: a `structlog` processor reads `trace.get_current_span().get_span_context()` and adds `trace_id`, `span_id`, `logging.googleapis.com/trace`, and `logging.googleapis.com/spanId` only when the context is valid.
1. **Describe agent work** with current GenAI semantic conventions: model calls carry `gen_ai.operation.name`, provider and request model, and input/output token usage; agent and tool spans carry their stable agent or tool names. Do not record prompt or completion bodies by default.
1. **Export on Google Cloud** through the Google-built OpenTelemetry Collector as a Cloud Run sidecar. Send OTLP to `http://localhost:4317`; let the collector authenticate with ADC and forward telemetry to Google Cloud.
1. **Evaluate separately**: operational telemetry detects failures and drift but does not prove response quality. Link a trace ID to Langfuse or MLflow scores when used, and keep repeated baseline-versus-candidate trials in the project's evaluation workflow.
1. **Verify all three signals**: send one request, locate its trace, read the correlated log events, confirm the expected metric, then exercise shutdown to prove buffered telemetry flushes within the platform grace period.
   ```bash
   gcloud logging read 'trace="projects/<project>/traces/<trace_id>"' --limit=20
   ```

## Gotchas

- **Cloud Logging keys are exact**: plain `level` and `msg` are not promoted to severity and message fields.
- **Sampling follows the parent**: use `parentbased_traceidratio` with a measured production ratio; keep 100% sampling for bounded development only.
- **Cardinality is a budget**: do not put user IDs, raw URL IDs, prompts, errors, or tool arguments in metric labels.
- **Telemetry is best effort**: bound exporter queues and timeouts, handle `SIGTERM`, and never block a user request on an unavailable collector.
- **Privacy starts before export**: redact secrets and personal data in the application, because backend filters cannot retract already-exported spans or logs.

## Official Skills

Upstream: `langfuse/skills`, `mlflow/skills`, `pydantic/skills`, and `grafana/skills`. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and install only the backend selection the project uses.

## Documentation

- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) · [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) · [Cloud Logging structured logs](https://docs.cloud.google.com/logging/docs/structured-logging) · [Google-built OTel Collector](https://docs.cloud.google.com/stackdriver/docs/instrumentation/google-built-otel)
- Companion skills: [python-stack](../python-stack/SKILL.md), [quality-assurance](../quality-assurance/SKILL.md), [cloud-run](../cloud-run/SKILL.md), [google-adk](../google-adk/SKILL.md), [gcloud](../gcloud/SKILL.md), [benchmark](../benchmark/SKILL.md).
