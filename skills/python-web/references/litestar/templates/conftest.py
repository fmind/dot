"""Opt-in integration-test fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from testcontainers.community.postgres import PostgresContainer

# Settings load when the package is imported; CI has no .env, so default to an unreachable
# database for the offline gate. A real environment value still wins.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unavailable.invalid/test")

# Digest-pinned so integration runs are reproducible; refresh the tag and digest with upgrade-tools.
POSTGRES_IMAGE = "postgres:18.6-alpine@sha256:10a5c69a83035ab5239f5620d708520e8b28f5aa1f2b20143e6024532edadfb5"


@pytest.fixture(scope="session")
def postgres_database_url() -> Iterator[str]:
    """Start PostgreSQL only for tests that request this fixture."""
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
