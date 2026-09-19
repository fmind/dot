# Session Compatibility

Read this before changing discovery, parser output, replacement rules, or storage. [store.py](../../../../dot/src/fmind_dot/archive/store.py), [sync.py](../../../../dot/src/fmind_dot/archive/sync.py), [parsers.py](../../../../dot/src/fmind_dot/archive/parsers.py), and [query.py](../../../../dot/src/fmind_dot/archive/query.py) define current behavior; do not treat a remembered version number as current.

## Change boundary

1. Identify whether the change affects source discovery, normalized transcript bytes, usage extraction, the bundle manifest, or queries. Check callers in `agent.py` and the matching parser/store/query tests.
1. For changed normalized output from the same source, bump `SESSION_PARSER_VERSION`: sync reparses every source whose stored parser differs and replaces the copy when the new parse has at least as many records. Evaluate `SESSION_SCHEMA_VERSION` and `SESSION_STORE_VERSION` separately when the bundle structure or layout changes; a new store needs a migration from the previous one that never modifies the old store.
1. Preserve the replacement rules: one bundle per agent and session; never replace with fewer records; never replace when usage extraction fails (a new session keeps its transcript without usage and retries on the next sync). Keep the stat signature complete enough that sync never skips a changed source.
1. Keep owner-only permissions, atomic file replacement, and safe path components for agent and session identities. Keep private transcript content out of fixtures and diagnostic output; use synthetic records.
1. Test repeated sync, truncated sources, failed usage, malformed input, migration, and query selection. Verify that unsupported formats stop queries and sync before mutation.

## Useful evidence

- [Parser tests](../../../../dot/tests/test_agent_parsers.py): source snapshots, malformed records, supported formats, and usage metrics.
- [Storage tests](../../../../dot/tests/test_session_store.py): bundle layout, private permissions, replacement rules, and corruption.
- [Transaction tests](../../../../dot/tests/test_archive_transaction.py): incremental sync, usage retention, and v2 migration.
- [Query tests](../../../../dot/tests/test_session_query.py): status, filters, and archive retrieval.

The active store is `sessions/v3`: each `<agent>/<session_id>.jsonl` holds a manifest line (schema 3, including `usage` and the source signature) followed by normalized records. `SESSION_PARSER_VERSION` and `READABLE_PARSER_VERSIONS` in `store.py` own the current and readable parser versions, documented in [contracts](../../../../skills/dot-cli/references/contracts.md). Parsers 3 and 4 arrive only through the v2 migration and are flagged as legacy accounting until sync recaptures their sources. The first archive access migrates `sessions/v2` by keeping the generation with the most records (newest on ties) and the newest available usage; `sessions/v2` stays untouched for the owner to remove. Provider-source pruning is outside Dot.
