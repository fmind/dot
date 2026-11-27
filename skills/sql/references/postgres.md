---
name: postgres
description: "Inspect PostgreSQL and pgvector safely via psql and Cloud SQL Auth Proxy: read-only timeouts, EXPLAIN plans, locks."
---

# PostgreSQL CLI (`psql`) & Live Diagnostics

Inspect PostgreSQL and `pgvector` instances safely via `psql` without blocking production traffic, hanging on pagers, or leaking credentials. Application pools, SQLAlchemy, and Alembic migrations live in [python/database-and-jobs](../../python/references/database-and-jobs.md); vector schema design lives in [rag-and-vectors](../../agent-frameworks/references/rag-and-vectors.md).

## Safe Read-Only Invocation

Pin non-interactive, fail-closed, read-only flags on every ad-hoc diagnostic call:

```bash
PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=2000' \
  psql -X -v ON_ERROR_STOP=1 --pset=pager=off --csv \
  -c "SELECT current_database(), current_user, pg_is_in_recovery();"
```

- **`-X`**: skips `~/.psqlrc` so personal aliases/settings never alter output.
- **`-v ON_ERROR_STOP=1 --pset=pager=off`**: exits non-zero on the first SQL error and avoids interactive pager hangs.
- **`PGOPTIONS`**: enforces read-only transactions plus bounded statement (`10s`) and lock (`2s`) timeouts so queries cannot stall pools or mutate data.
- **Credentials**: never pass passwords via `PGPASSWORD` or `postgresql://user:pass@...` on `argv` or shell history; prefer IAM auth (`cloud-sql-proxy --auto-iam-authn` on `127.0.0.1`) or a `0600` `PGPASSFILE` (`~/.pgpass`) over `PGPASSWORD` env even under `with-secret` ([authentication](../../dot-cli/references/authentication.md)).

## Diagnostics Workflow

1. **Verify target & replica role**: confirm `current_database()`, `current_user`, and `pg_is_in_recovery()` before running scans; route heavy reads and `EXPLAIN` probes to a read replica when available.
1. **Inspect query plans safely**: wrap `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` in `BEGIN READ ONLY; ... ROLLBACK;` (never run `EXPLAIN ANALYZE` on mutating DML outside a rolled-back transaction). Look for sequential scans on large tables, row-estimate skew, high shared buffer reads, or disk temp spills.
1. **Check active sessions, locks & bloat**:
   - Active/blocked queries: filter `pg_stat_activity` (`state <> 'idle'`) joined with `pg_blocking_pids(pid)` and `pg_locks`.
   - Table/index footprint & scan ratios: inspect `pg_total_relation_size`, `pg_stat_user_tables` (`seq_scan` vs `idx_scan`, `n_dead_tup`), and unused indexes in `pg_stat_user_indexes`.
1. **Verify `pgvector` index usage**: confirm index type (`hnsw` vs `ivfflat`), operator class matching the query operator (`vector_cosine_ops` with `<=>`, `vector_l2_ops` with `<->`), and filtered query plans (`SET LOCAL hnsw.iterative_scan = strict_order;` when metadata filters drop recall).

## Boundaries & Gotchas

- **No ad-hoc production DDL or data edits**: schema changes (`CREATE INDEX CONCURRENTLY`, expand-contract column drops) and backfills require explicit authorization and belong in versioned Alembic migrations, not one-off `psql` commands.
- **Beware `LOCK TABLE` & long idle transactions**: `idle in transaction` sessions block `VACUUM` and `CREATE INDEX CONCURRENTLY`; keep diagnostic transactions short.
- **Audit**: validate SQL semantics and plans with `fmind-review-data` and lock/timeout risk with `fmind-review-sre` ([subagent](../../subagent/SKILL.md)).

## Documentation

- [PostgreSQL psql reference](https://www.postgresql.org/docs/current/app-psql.html) · [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) · [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy) · [pgvector](https://github.com/pgvector/pgvector)
- Companions: [quality-and-dbt](quality-and-dbt.md), [python/database-and-jobs](../../python/references/database-and-jobs.md), [rag-and-vectors](../../agent-frameworks/references/rag-and-vectors.md), [gcloud](../../gcloud/SKILL.md).
