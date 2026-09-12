---
name: data-migration
description: Evolve schemas, Alembic migrations, file formats, and archive generations with rehearsed recovery. Use when existing persisted data must survive a change.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/data-migration
  created: "2026-09-09"
  updated: "2026-09-11"
---

# Data Migration

Change persisted data while preserving its declared meaning and recovery path. [django](../django/SKILL.md) owns Django migration mechanics; [production-readiness](../production-readiness/SKILL.md) owns the launch decision, and [duckdb](../duckdb/SKILL.md) owns ad-hoc analysis.

## Workflow

1. **Inventory the boundary**: identify source and target versions, authoritative data versus rebuildable caches, all readers and writers, active locks, scale, and compatibility requirements. Inspect actual stored versions rather than inferring them from current code.
1. **Define invariants**: specify identity, counts, relationships, ordering, encoding, null semantics, and fields intentionally changed or discarded. Reject unsupported versions and malformed input with a recoverable error; do not silently reinterpret them.
1. **Choose the transition**: use the project's migration engine for databases. For mixed deployed readers, expand compatibility, backfill, switch readers, then contract only after old readers are retired. For files or immutable archives, write a new versioned generation and retain the old one.
1. **Prepare recovery**: take a consistent snapshot and prove it can be restored and read in isolation. Record disk needs, lock duration, the rollback cutoff, and treatment of writes after that cutoff. A schema downgrade is not necessarily data recovery.
1. **Implement resumably**: use transactional units or atomic generation publication. Commit progress with the corresponding data, use stable identities, and make retries skip verified completed units. Bind checkpoints to input identity and migration version; reject a resume against changed input.
1. **Rehearse failures**: use representative old data plus empty, malformed, Unicode, duplicate, and boundary-sized cases. Interrupt before and after data/checkpoint publication, resume, and compare with an uninterrupted result. Test a second invocation and old-reader compatibility where promised.
1. **Execute within scope**: production mutation or intentional data loss requires its specific authority; prepare the migration diff, rehearsal results, duration, and recovery plan before requesting any missing approval. Preserve applied migration history.
1. **Verify and report**: read the result through the application, check the declared invariants, inspect migration status, and report migrated, rejected, and unresolved units separately. Keep the old generation or backup until the retention decision is authorized.

## Storage details

- **Alembic**: follow [Alembic migrations](references/alembic.md) for metadata wiring, autogeneration review, revision heads, and upgrade rehearsal against the selected database.
- **SQLite**: follow [SQLite rehearsal](references/sqlite.md) for WAL-safe snapshots, transactions, and integrity checks; a main-file copy during active writes is insufficient.
- **Files**: stage output on the target filesystem, flush and sync as required by the durability contract, validate it, then atomically publish a manifest or pointer. Multi-file renames are not one transaction. Preserve required permissions and never overwrite an immutable generation in place.
- **Caches**: rebuild only when the authoritative input and the selected parser/version can reproduce them. A rebuild is not a substitute for migrating unique source data.

## Documentation

- [SQLite backup](https://www.sqlite.org/backup.html) · [SQLite transactions](https://www.sqlite.org/lang_transaction.html) · [Django migrations](https://docs.djangoproject.com/en/stable/topics/migrations/)
- Releases: [Alembic changelog](https://alembic.sqlalchemy.org/en/latest/changelog.html)
- Companion skills: [test-driven-development](../test-driven-development/SKILL.md) (regression and property tests), [implementation-plan](../implementation-plan/SKILL.md) (ordered rollout).
