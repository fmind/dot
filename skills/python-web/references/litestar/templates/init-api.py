"""<description>."""

from __future__ import annotations

import argparse
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any, Literal

import structlog
from granian import Granian
from granian.constants import Interfaces
from granian.server import MPServer, MTServer
from litestar import Litestar, Request, Response, get
from litestar.config.cors import CORSConfig
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from <package>.telemetry import configure_logging, configure_otel

__version__ = version("<slug>")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins: list[str] = Field(default_factory=list)
    environment: Literal["development", "test", "production"] = "production"
    host: str = "127.0.0.1"
    port: int = 8000


logger = structlog.get_logger()


@get("/health")
async def health_check() -> dict[str, str]:
    """Report process liveness without touching external dependencies."""
    return {"status": "healthy"}


def handle_internal_error(request: Request[Any, Any, Any], exc: Exception) -> Response[dict[str, object]]:
    """Log only exception type and path on 500s so tracebacks and secret strings stay out of responses and logs."""
    logger.error("Unhandled internal error", error=type(exc).__name__, path=request.url.path)
    return Response({"status_code": 500, "detail": "Internal Server Error"}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)


def create_app(config: Settings) -> Litestar:
    """Build a stateless ASGI application with redacted JSON logging and optional OTLP telemetry."""
    configure_logging()

    @asynccontextmanager
    async def telemetry_lifespan(_: Litestar) -> AsyncGenerator[None]:
        tracer_provider, meter_provider = configure_otel("<slug>")
        try:
            yield
        finally:
            if meter_provider is not None:
                meter_provider.shutdown()
            if tracer_provider is not None:
                tracer_provider.shutdown()

    return Litestar(
        route_handlers=[health_check],
        cors_config=CORSConfig(allow_origins=config.cors_origins),
        exception_handlers={HTTP_500_INTERNAL_SERVER_ERROR: handle_internal_error},
        lifespan=[telemetry_lifespan],
        logging_config=None,
    )


def create_default_app() -> Litestar:
    """Build the ASGI application from runtime environment settings."""
    return create_app(Settings())


# Granian aliases MPServer or MTServer by interpreter build, which type checkers reject as a type.
def create_server(config: Settings) -> MPServer | MTServer:
    """Configure Granian without starting a worker process."""
    target = f"{__name__}:create_default_app"
    return Granian(
        target,
        interface=Interfaces.ASGI,
        port=config.port,
        address=config.host,
        reload=config.environment == "development",
        factory=True,
        log_dictconfig={"loggers": {"_granian": {"handlers": [], "propagate": True}}},
    )


def build_parser() -> argparse.ArgumentParser:
    """Define CLI flags so `--help` and `--version` stay free of runtime side effects."""
    parser = argparse.ArgumentParser(
        prog="<slug>", description="<description>.", allow_abbrev=False, suggest_on_error=True
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entrypoint invoked by the `<slug>` console script or `uv run`."""
    build_parser().parse_args(argv)
    config = Settings()
    logger.info(
        "Starting <slug> API server",
        host=config.host,
        port=config.port,
        environment=config.environment,
    )
    create_server(config).serve()
