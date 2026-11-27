"""<description>."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncGenerator, Awaitable, Sequence
from contextlib import asynccontextmanager
from http import HTTPStatus
from importlib.metadata import version
from typing import Any, Literal, Protocol

import structlog
from granian import Granian
from granian.constants import Interfaces
from granian.server import MPServer, MTServer
from litestar import Litestar, Request, Response, get
from litestar.config.cors import CORSConfig
from litestar.datastructures import MutableScopeHeaders
from litestar.di import NamedDependency, Provide
from litestar.exceptions import HTTPException
from litestar.middleware import ASGIMiddleware
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.types import ASGIApp, Message, Receive, Scope, Send
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from <package>.telemetry import configure_logging, configure_otel

__version__ = version("<slug>")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: SecretStr
    cors_origins: list[str] = Field(default_factory=list)
    environment: Literal["development", "test", "production"] = "production"
    host: str = "127.0.0.1"
    port: int = 8000


logger = structlog.get_logger()


@get("/health")
async def health_check() -> dict[str, str]:
    """Report process liveness without touching external dependencies."""
    return {"status": "healthy"}


class _ExecutableSession(Protocol):
    def execute(self, statement: TextClause, /) -> Awaitable[object]: ...


async def check_readiness(db_session: _ExecutableSession, *, timeout_seconds: float = 5.0) -> Response[dict[str, str]]:
    """Report whether the database dependency can serve traffic."""
    try:
        # Bound pool acquisition, connection establishment, and query execution together.
        async with asyncio.timeout(timeout_seconds):
            await db_session.execute(text("SELECT 1"))
        return Response({"status": "ready", "database": "connected"}, status_code=200)
    except (SQLAlchemyError, OSError) as error:
        # OSError includes TimeoutError; external cancellation must still propagate.
        logger.warning("Readiness check database error", error=type(error).__name__)
        return Response({"status": "not_ready", "database": "disconnected"}, status_code=503)


@get("/ready")
async def readiness_check(db_session: NamedDependency[AsyncSession]) -> Response[dict[str, str]]:
    """Expose the dependency readiness check through HTTP."""
    return await check_readiness(db_session)


class _Shutdownable(Protocol):
    def shutdown(self) -> object: ...


async def _shutdown_provider(provider: _Shutdownable | None, name: str, *, timeout_seconds: float = 5.0) -> None:
    """Flush and close an OTel provider off the event loop without masking subsequent cleanup."""
    if provider is None:
        return
    try:
        async with asyncio.timeout(timeout_seconds):
            await asyncio.to_thread(provider.shutdown)
    except (OSError, RuntimeError) as error:
        logger.warning("Telemetry shutdown failed", provider=name, error=type(error).__name__)


class SecurityHeadersMiddleware(ASGIMiddleware):
    """Attach baseline HTTP security headers per app instance without sharing handler caches."""

    def __init__(self, *, hsts: bool) -> None:
        headers: list[tuple[str, str]] = [
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "strict-origin-when-cross-origin"),
            ("X-Frame-Options", "DENY"),
            ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
            ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
        ]
        if hsts:
            headers.append(("Strict-Transport-Security", "max-age=31536000; includeSubDomains"))
        self._headers = tuple(headers)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableScopeHeaders.from_message(message=message)
                for key, value in self._headers:
                    headers.setdefault(key, value)
            await send(message)

        await next_app(scope, receive, send_with_headers)


def handle_http_error(request: Request[Any, Any, Any], exc: HTTPException) -> Response[dict[str, object]]:
    """Return RFC 9457 Problem Details for HTTP errors while redacting 5xx details."""
    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "HTTP Error"
    detail = exc.detail if exc.status_code < HTTP_500_INTERNAL_SERVER_ERROR and exc.detail else title
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("Unhandled HTTP server error", status_code=exc.status_code, path=request.url.path)
    return Response(
        {
            "type": "about:blank",
            "title": title,
            "status": exc.status_code,
            "detail": detail,
            "instance": request.url.path,
        },
        status_code=exc.status_code,
        headers=exc.headers,
        media_type="application/problem+json",
    )


def handle_internal_error(request: Request[Any, Any, Any], exc: Exception) -> Response[dict[str, object]]:
    """Return RFC 9457 Problem Details and log only exception type and path on 500s."""
    logger.error("Unhandled internal error", error=type(exc).__name__, path=request.url.path)
    return Response(
        {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "Internal Server Error",
            "instance": request.url.path,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/problem+json",
    )


def create_app(config: Settings) -> Litestar:
    """Build an application whose database and telemetry resources follow its lifespan."""
    configure_logging()
    engine = create_async_engine(
        config.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        # asyncpg syntax; psycopg uses {"options": "-c statement_timeout=10000"}.
        connect_args={"server_settings": {"statement_timeout": "10000"}},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def provide_db_session() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    @asynccontextmanager
    async def app_lifespan(_: Litestar) -> AsyncGenerator[None]:
        tracer_provider, meter_provider = configure_otel("<slug>")
        try:
            yield
        finally:
            try:
                try:
                    await _shutdown_provider(meter_provider, "meter")
                finally:
                    await _shutdown_provider(tracer_provider, "tracer")
            finally:
                await engine.dispose()

    return Litestar(
        route_handlers=[health_check, readiness_check],
        middleware=[SecurityHeadersMiddleware(hsts=config.environment == "production")],
        dependencies={"db_session": Provide(provide_db_session)},
        cors_config=CORSConfig(allow_origins=config.cors_origins),
        exception_handlers={
            HTTPException: handle_http_error,
            HTTP_500_INTERNAL_SERVER_ERROR: handle_internal_error,
        },
        request_max_body_size=1_048_576,
        lifespan=[app_lifespan],
        logging_config=None,
    )


def create_default_app() -> Litestar:
    """Build the ASGI application from runtime environment settings."""
    return create_app(Settings())


# Granian aliases MPServer or MTServer by interpreter build, which type checkers reject as a type.
def create_server(config: Settings) -> MPServer | MTServer:
    """Configure Granian without starting a worker process."""
    # The import package is the ASGI factory target; the distribution/command may contain hyphens.
    target = f"{__name__}:create_default_app"

    return Granian(
        target,
        interface=Interfaces.ASGI,
        port=config.port,
        address=config.host,
        reload=config.environment == "development",
        factory=True,
        # Granian's own logger skips the root JSON handler configure_logging() installs unless it propagates.
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
    configure_logging()
    config = Settings()
    logger.info(
        "Starting <slug> web server",
        host=config.host,
        port=config.port,
        environment=config.environment,
    )
    create_server(config).serve()
