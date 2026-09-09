# Session Compatibility

Read this before changing discovery, parser output, generation identity, or storage. [session_store.py](../../../../dot/src/fmind_dot/session_store.py), [agent_parsers.py](../../../../dot/src/fmind_dot/agent_parsers.py), and [session_query.py](../../../../dot/src/fmind_dot/session_query.py) define current behavior; do not treat a remembered version number as current.

## Change boundary

1. Identify whether the change affects source discovery, normalized transcript bytes, usage extraction, manifests, or filesystem-generation queries. Check callers in `agent.py` and the matching parser/store/query tests.
1. For changed normalized output from the same source, assess `SESSION_PARSER_VERSION`: generation identity includes parser version and source fingerprint. Use a new parser generation for changed normalization instead of rewriting an existing immutable archive. Evaluate `SESSION_SCHEMA_VERSION` and `SESSION_STORE_VERSION` separately when stored structure or layout changes.
1. Define how old generations remain readable, how current-generation selection behaves, and whether retained source data permits reingestion. A version bump alone is not a completed migration; make any migration explicit, recoverable, and bounded to the authorized store.
1. Preserve source-byte fingerprints, completeness and malformed-record accounting, owner-only permissions, atomic publication, and rejection of unsafe identities or linked paths. Keep private transcript content out of fixtures and diagnostic output; use synthetic records.
1. Test old and new generations together, repeated ingestion, interrupted or conflicting publication, malformed input, and query selection as relevant to the changed boundary. Compaction must retain unknown formats and stop on integrity failures; never use cleanup to disguise a migration failure.

## Useful evidence

- [Parser tests](../../../../dot/tests/test_agent_parsers.py): source snapshots, malformed records, supported formats, and usage metrics.
- [Storage tests](../../../../dot/tests/test_session_store.py): immutable identity, private permissions, atomicity, races, and corruption.
- [Query tests](../../../../dot/tests/test_session_query.py): current generations and archive retrieval.
- [Doctor tests](../../../../dot/tests/test_agent_doctor.py): integration and archive health. Routine queries do not require a deep workstation audit.
