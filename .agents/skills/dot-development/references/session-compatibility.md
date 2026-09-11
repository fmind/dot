# Session Compatibility

Read this before changing discovery, parser output, generation identity, or storage. [store.py](../../../../dot/src/fmind_dot/archive/store.py), [parsers.py](../../../../dot/src/fmind_dot/archive/parsers.py), and [query.py](../../../../dot/src/fmind_dot/archive/query.py) define current behavior; do not treat a remembered version number as current.

## Change boundary

1. Identify whether the change affects source discovery, normalized transcript bytes, usage extraction, manifests, or filesystem-generation queries. Check callers in `agent.py` and the matching parser/store/query tests.
1. For changed normalized output from the same source, assess `SESSION_PARSER_VERSION`: generation identity includes parser version and source fingerprint. Use a new parser generation for changed normalization instead of rewriting an existing immutable archive. Evaluate `SESSION_SCHEMA_VERSION` and `SESSION_STORE_VERSION` separately when stored structure or layout changes.
1. Support only explicitly admitted parser generations in the active store and bundle schema. Reject unsupported versions with a clear error; never silently adopt, convert, or delete another store. Define current-generation selection and whether retained source data permits recapture.
1. Preserve source-byte fingerprints, completeness and malformed-record accounting, owner-only permissions, atomic publication, and rejection of unsafe identities or linked paths. Keep private transcript content out of fixtures and diagnostic output; use synthetic records.
1. Test repeated ingestion, interrupted or conflicting publication, malformed input, and query selection. Verify that unsupported formats stop queries and compaction before mutation, and that retired storage remains untouched.

## Useful evidence

- [Parser tests](../../../../dot/tests/test_agent_parsers.py): source snapshots, malformed records, supported formats, and usage metrics.
- [Storage tests](../../../../dot/tests/test_session_store.py): immutable identity, private permissions, atomicity, races, and corruption.
- [Query tests](../../../../dot/tests/test_session_query.py): current generations and archive retrieval.
- [Doctor tests](../../../../dot/tests/test_agent_doctor.py): integration and archive health. Routine queries do not require a deep workstation audit.

Manifest schema 2 / parser 4 includes `usage.json` in validation, publication, and compaction. Never update usage separately from the transcript. The active store is `sessions/v2`. Parser 4 deduplicates Claude streaming usage and adds reconciled timestamped request samples for Claude/Codex. Parser 3 bundles remain readable for recovery, with legacy accounting flagged; usage selects the highest admitted parser, then latest ingestion per session. Recapture creates a new generation only from available sources and never rewrites parser 3. Parser 1/2, schema 1, and standalone usage remain unsupported. Compaction keeps parser generations separate. Provider-source pruning is outside Dot.
