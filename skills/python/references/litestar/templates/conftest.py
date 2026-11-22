"""Opt-in integration-test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from testcontainers.community.postgres import PostgresContainer

# Digest-pinned so integration runs are reproducible; refresh the tag and digest with upgrade-tools.
POSTGRES_IMAGE = "postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395"


@pytest.fixture(scope="session")
def postgres_database_url() -> Iterator[str]:
    """Start PostgreSQL only for tests that request this fixture."""
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
