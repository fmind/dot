"""Structured JSON logging and OTLP telemetry helpers for Python services."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _format_cloud_event(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    if (level := event_dict.pop("level", None)) is not None:
        event_dict["severity"] = str(level).upper()
    if (event := event_dict.pop("event", None)) is not None:
        event_dict["message"] = event
    if exc_info := event_dict.pop("exc_info", None):
        if isinstance(exc_info, BaseException):
            event_dict["error_type"] = type(exc_info).__name__
        elif isinstance(exc_info, tuple) and exc_info and exc_info[0] is not None:
            event_dict["error_type"] = exc_info[0].__name__
        elif exc_info is True:
            _, exc, _ = sys.exc_info()
            if exc is not None:
                event_dict["error_type"] = type(exc).__name__
    event_dict.pop("exception", None)
    event_dict.pop("stack_info", None)
    span_ctx = trace.get_current_span().get_span_context()
    if span_ctx.is_valid:
        trace_hex = f"{span_ctx.trace_id:032x}"
        span_hex = f"{span_ctx.span_id:016x}"
        event_dict["trace_id"] = trace_hex
        event_dict["span_id"] = span_hex
        if project := os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip():
            event_dict["logging.googleapis.com/trace"] = f"projects/{project}/traces/{trace_hex}"
            event_dict["logging.googleapis.com/spanId"] = span_hex
    return event_dict


def configure_logging(*, level: int = logging.INFO) -> None:
    """Configure structlog and stdlib logging as redacted JSON lines on stdout."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
        _format_cloud_event,
    ]
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, structlog.processors.JSONRenderer()],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def configure_otel(service_name: str) -> tuple[TracerProvider | None, MeterProvider | None]:
    """Configure HTTP OTLP traces and metrics only when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return None, None
    resolved_service = os.environ.get("OTEL_SERVICE_NAME", "").strip() or service_name
    resource = Resource.create({"service.name": resolved_service})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(timeout=5)))
    try:
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter(timeout=5))],
        )
    except BaseException:
        tracer_provider.shutdown()
        raise
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    return tracer_provider, meter_provider
