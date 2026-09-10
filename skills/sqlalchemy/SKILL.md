---
name: sqlalchemy
description: Build SQLAlchemy database access and Alembic migrations. Use for ORM queries, transactions, async sessions, migration autogeneration, revision heads, and schema upgrades.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sqlalchemy
  created: "2026-09-10"
  updated: "2026-09-10"
---

# SQLAlchemy

Use SQLAlchemy for relational database access; [data-migration](../data-migration/SKILL.md) owns migration and recovery procedure, and [pydantic](../pydantic/SKILL.md) owns external input models.

## Workflow

1. Inspect the locked SQLAlchemy version, database dialect/driver, connection configuration, and existing migration tooling. Add `sqlalchemy` with `uv add sqlalchemy` and the selected driver; use the asyncio extra when required by the chosen release.
1. Choose Core for explicit SQL expressions or ORM for object relationships. For modern ORM code, use `DeclarativeBase`, `Mapped`, `mapped_column`, and `select`; preserve an intentional legacy API until migration is in scope.
1. Reuse an engine per application lifecycle and scope sessions to a request or unit of work. Use a transaction context such as `with Session(engine) as session, session.begin():` so failures roll back and resources close.
1. Bind query parameters instead of interpolating SQL. Declare uniqueness, foreign keys, nullability, and indexes in the database; validate input before executing queries.
1. Load relationships deliberately to avoid N+1 queries and unexpected lazy IO. Inspect emitted SQL and query counts on representative data; add an index only with evidence from the target database.
1. Test insert/read/update/delete, constraint violations, rollback, and session cleanup in an isolated database. Test dialect-specific behavior against the actual database engine before claiming compatibility.
1. Follow [Alembic migrations](references/alembic.md) for persistent schema changes: metadata wiring, generated-operation review, revision heads, and upgrade rehearsal. `metadata.create_all()` is suitable for disposable fixtures, not schema upgrades.

## Gotchas

- A `Session` is mutable transaction state; use one per thread, and one `AsyncSession` per concurrent task. Do not share sessions across `asyncio.gather` calls.
- Flush is not commit. After a failed flush, roll back before reusing a session; avoid returning ORM objects whose later serialization triggers IO after session closure.
- Async code needs an async driver and explicit IO boundaries; eager loading can prevent implicit lazy queries. Close sessions and dispose the engine during shutdown; [python-async](../python-async/SKILL.md) owns task cancellation and lifetime.
- SQL logs and connection URLs can expose credentials and values. SQLite fixtures do not prove PostgreSQL locking, type, or concurrency behavior.

## Official Skills

No consumer Agent Skill was found in the inspected [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) repository on 2026-09-10. Use the official documentation below; community ORM packages are not SQLAlchemy-maintained skills.

## Documentation

- [Unified tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) · [Sessions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) · [Asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) · [Alembic](https://alembic.sqlalchemy.org/en/latest/)
