from __future__ import annotations

import asyncio
import json
import logging
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
import structlog
from granian.server import MPServer
from litestar import get
from litestar.testing import AsyncTestClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from <package> import (
    Settings,
    __version__,
    check_readiness,
    create_app,
    create_default_app,
    create_server,
    handle_internal_error,
    main,
)
from <package> import __main__ as module_entrypoint
from <package>.telemetry import configure_logging, configure_otel


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _isolated_settings_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep developer `.env` files and ambient service variables out of unit tests."""
    monkeypatch.chdir(tmp_path)
    for variable in (
        "DATABASE_URL",
        "CORS_ORIGINS",
        "ENVIRONMENT",
        "GOOGLE_CLOUD_PROJECT",
        "HOST",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
        "PORT",
    ):
        monkeypatch.delenv(variable, raising=False)


class HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


class UnhealthySession:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def execute(self, _statement: object) -> None:
        raise self.error


class WaitingSession:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def execute(self, _statement: object) -> None:
        try:
            self.started.set()
            await asyncio.Event().wait()
        finally:
            self.cleaned.set()


def test_cors_is_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unavailable.invalid/test")
    app = create_default_app()

    assert app.cors_config
    assert app.cors_config.allow_origins == []
    assert app.request_max_body_size == 1_048_576


@pytest.mark.anyio
async def test_http_error_returns_problem_details() -> None:
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")

    async with AsyncTestClient(app=create_app(config)) as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert body["instance"] == "/missing"
    assert isinstance(body["detail"], str)
    assert body["detail"]


@pytest.mark.anyio
async def test_health_check_is_dependency_free() -> None:
    assert configure_otel("<slug>") == (None, None)
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")

    async with AsyncTestClient(app=create_app(config)) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in response.headers


@pytest.mark.anyio
async def test_production_sets_hsts_header() -> None:
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="production")

    async with AsyncTestClient(app=create_app(config)) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.anyio
async def test_readiness_check_success() -> None:
    response = await check_readiness(HealthySession())

    assert response.status_code == 200
    assert response.content == {"status": "ready", "database": "connected"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error", [SQLAlchemyError("database unavailable"), ConnectionRefusedError("connection refused")]
)
async def test_readiness_check_failure(error: Exception) -> None:
    response = await check_readiness(UnhealthySession(error))

    assert response.status_code == 503
    assert response.content == {"status": "not_ready", "database": "disconnected"}


@pytest.mark.anyio
async def test_readiness_deadline_cancels_a_stalled_query() -> None:
    session = WaitingSession()

    response = await check_readiness(session, timeout_seconds=0)

    assert response.status_code == 503
    assert response.content == {"status": "not_ready", "database": "disconnected"}
    assert session.cleaned.is_set()


@pytest.mark.anyio
async def test_readiness_preserves_external_cancellation() -> None:
    session = WaitingSession()

    async with asyncio.timeout(5):
        task = asyncio.create_task(check_readiness(session))
        await session.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert session.cleaned.is_set()


@pytest.mark.anyio
async def test_readiness_reports_503_when_the_database_is_unreachable() -> None:
    # Reserve a loopback port without listening: refusal is local and needs no DNS.
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        config = Settings(database_url=SecretStr(f"postgresql+asyncpg://127.0.0.1:{port}/test"), environment="test")

        async with AsyncTestClient(app=create_app(config)) as client:
            response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "disconnected"}


@pytest.mark.anyio
async def test_internal_error_redacts_exception_details(capsys: pytest.CaptureFixture[str]) -> None:
    @get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("SYNTHETIC_SECRET_MARKER")

    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")
    app = create_app(config)
    app.register(boom)

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Internal Server Error",
        "instance": "/boom",
    }
    out = capsys.readouterr().out
    assert "SYNTHETIC_SECRET_MARKER" not in out
    records = [json.loads(line) for line in out.strip().splitlines() if line.startswith("{")]
    error_record = next(item for item in records if item.get("message") == "Unhandled internal error")
    assert error_record["severity"] == "ERROR"
    assert error_record["error"] == "RuntimeError"
    assert error_record["path"] == "/boom"
    assert callable(handle_internal_error)


@pytest.mark.anyio
async def test_telemetry_redacts_exceptions_and_correlates_spans(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "override-service")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "example-project")
    tracer_provider, meter_provider = configure_otel("<slug>")
    assert isinstance(tracer_provider, TracerProvider)
    assert isinstance(meter_provider, MeterProvider)
    assert tracer_provider.resource.attributes["service.name"] == "override-service"
    try:
        configure_logging(level=logging.INFO)
        log = structlog.get_logger("telemetry_test")
        with tracer_provider.get_tracer("test").start_as_current_span("op"):
            log.info("direct_exc", exc_info=RuntimeError("SECRET_ONE"))
            try:
                raise ValueError("SECRET_TWO")
            except ValueError:
                log.warning("active_exc", exc_info=True)
            log.info("tuple_exc", exc_info=(KeyError, KeyError("SECRET_THREE"), None))
    finally:
        try:
            meter_provider.shutdown()
        finally:
            tracer_provider.shutdown()

    out = capsys.readouterr().out
    for marker in ("SECRET_ONE", "SECRET_TWO", "SECRET_THREE"):
        assert marker not in out
    events = {json.loads(line)["message"]: json.loads(line) for line in out.strip().splitlines() if line.startswith("{")}
    assert events["direct_exc"]["error_type"] == "RuntimeError"
    assert events["active_exc"]["error_type"] == "ValueError"
    assert events["tuple_exc"]["error_type"] == "KeyError"
    assert "trace_id" in events["direct_exc"]
    assert events["direct_exc"]["logging.googleapis.com/trace"].startswith("projects/example-project/traces/")


@pytest.mark.anyio
async def test_lifespan_shuts_down_configured_otel_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fail_meter() -> None:
        calls.append("meter")
        raise RuntimeError("collector unreachable")

    fake_tracer = SimpleNamespace(shutdown=lambda: calls.append("tracer"))
    fake_meter = SimpleNamespace(shutdown=fail_meter)
    monkeypatch.setattr("<package>.configure_otel", lambda _name: (fake_tracer, fake_meter))
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")

    async with AsyncTestClient(app=create_app(config)) as client:
        assert (await client.get("/health")).status_code == 200

    assert calls == ["meter", "tracer"]


def test_server_targets_the_app_factory() -> None:
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")
    server = create_server(config)

    assert server.target == "<package>:create_default_app"
    assert server.factory is True


def test_main_prints_version_without_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as raised:
        main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"{__version__}\n"


def test_main_starts_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unavailable.invalid/test")
    server = create_autospec(MPServer, instance=True, spec_set=True)
    monkeypatch.setattr("<package>.create_server", lambda _config: server)

    main([])

    server.serve.assert_called_once_with()


def test_module_entrypoint() -> None:
    assert module_entrypoint.__name__.endswith(".__main__")
    result = subprocess.run(
        [sys.executable, "-m", "<package>", "--version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{__version__}\n"
    assert result.stderr == ""
