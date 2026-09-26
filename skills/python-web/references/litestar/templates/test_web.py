from __future__ import annotations

import asyncio
import socket
from typing import cast
from unittest.mock import Mock

import pytest
from litestar.testing import AsyncTestClient
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from <package> import Settings, app, check_readiness, create_app, create_server, main, settings


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


def test_cors_is_closed_by_default() -> None:
    assert app.cors_config
    assert app.cors_config.allow_origins == []


@pytest.mark.anyio
async def test_health_check_is_dependency_free() -> None:
    config = Settings(database_url=SecretStr("postgresql+asyncpg://unavailable.invalid/test"), environment="test")

    async with AsyncTestClient(app=create_app(config)) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.anyio
async def test_readiness_check_success() -> None:
    response = await check_readiness(cast(AsyncSession, HealthySession()))

    assert response.status_code == 200
    assert response.content == {"status": "ready", "database": "connected"}


@pytest.mark.anyio
@pytest.mark.parametrize("error", [SQLAlchemyError("database unavailable"), ConnectionRefusedError("connection refused")])
async def test_readiness_check_failure(error: Exception) -> None:
    response = await check_readiness(cast(AsyncSession, UnhealthySession(error)))

    assert response.status_code == 503
    assert response.content == {"status": "not_ready", "database": "disconnected"}


@pytest.mark.anyio
async def test_readiness_deadline_cancels_a_stalled_query() -> None:
    session = WaitingSession()

    response = await check_readiness(cast(AsyncSession, session), timeout_seconds=0)

    assert response.status_code == 503
    assert response.content == {"status": "not_ready", "database": "disconnected"}
    assert session.cleaned.is_set()


@pytest.mark.anyio
async def test_readiness_preserves_external_cancellation() -> None:
    session = WaitingSession()

    async with asyncio.timeout(5):
        task = asyncio.create_task(check_readiness(cast(AsyncSession, session)))
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


def test_server_targets_the_import_package() -> None:
    server = create_server(settings)

    assert server.target == "<package>:app"


def test_main_starts_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Mock()
    monkeypatch.setattr("<package>.create_server", lambda _config: server)

    main()

    server.serve.assert_called_once_with()
