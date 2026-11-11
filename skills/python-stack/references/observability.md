---
name: observability
description: "Instrument Python services and agents: structlog logs, OpenTelemetry traces and metrics."
---

# Observability

Unified vendor-neutral Python telemetry: `structlog` JSON on stdout, OpenTelemetry traces + metrics over OTLP, and trace correlation on logs.

## Workflow

1. **Minimal packages**: lock `structlog`, OTel API/SDK, OTLP exporter, and active HTTP/framework instrumentors (`opentelemetry-instrumentation-httpx` splits `HTTPXClientInstrumentor` and `HTTPX2ClientInstrumentor`; FastAPI `0.142+` has native OTel per [fastapi](../../python-web/references/fastapi.md)). Avoid vendor SDKs in app code.
1. **Structured stdout logs**: emit one JSON line per event using `severity`, `message`, and `time` (Cloud Logging promotes those exact keys, not `level`/`msg`).
1. **OTLP config**: set `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_PROTOCOL`; disable export in local dev when unconfigured (SDK defaults otherwise dial `localhost`).
1. **Trace-log correlation**: inject `trace_id`, `span_id`, `logging.googleapis.com/trace`, and `logging.googleapis.com/spanId` from `trace.get_current_span().get_span_context()` when valid.
1. **GenAI spans without content leaks**: emit `gen_ai.operation.name`, provider/model, token counts, and stable agent/tool names. Suppress prompt/completion capture (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, leave `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` unset; note `EVENT_ONLY` still exports bodies as log events).
1. **Collector sidecar**: on Cloud Run, pair Google-built OTel Collector with matching protocol/port (`grpc` -> `http://localhost:4317`, `http/protobuf` -> `http://localhost:4318`) and ADC export; link trace IDs to Langfuse/MLflow scores for [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md).
1. **Verify logs, traces, metrics, and `SIGTERM` flush**:
   ```bash
   gcloud logging read 'trace="projects/<project>/traces/<trace_id>"' --project=<project> --freshness=1h --limit=20 --format='json(timestamp,severity,textPayload,jsonPayload.message,trace,spanId)'
   ```

## Gotchas & Upstream Skills

- **Sampling, cardinality, & resiliency**: use `parentbased_traceidratio` in prod (100% dev only); never put user IDs, raw URLs, prompts, errors, or tool args in metric labels; bound exporter queues/timeouts so collector outages never block requests; redact secrets/PII in-process before export.
- Upstream (`langfuse/skills`, `mlflow/skills`, `grafana/skills`): install per [vendor-skills](../../agent-project/references/vendor-skills.md).
- Docs: [OTel Python](https://opentelemetry.io/docs/languages/python/) · [OTLP](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/) · [GenAI semconv](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) · [Cloud Logging](https://docs.cloud.google.com/logging/docs/structured-logging) · [Google OTel Collector](https://docs.cloud.google.com/stackdriver/docs/instrumentation/google-built-otel) · [Releases](https://github.com/open-telemetry/opentelemetry-python/releases) · Companions: [foundation](foundation/GUIDE.md), [cloud-run](../../cloud-run/SKILL.md), [google-adk](../../agent-frameworks/references/google-adk.md), [gcloud](../../gcloud/SKILL.md), [performance](performance.md).
