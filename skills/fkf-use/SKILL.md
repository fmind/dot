---
name: fkf-use
description: Retrieve bounded local evidence with FKF. Use when resuming a project, recovering a decision, browsing source folders or labels, or reading exact evidence.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/fkf-use
  upstream: github.com/fmind/fkf
  upstream-sha256: "f44a62e0339c6269a787bfd1af5dea84b397bfbb520a5246457a25f5c6f3dacf"
  created: "2026-09-13"
  updated: "2026-09-13"
---

# Retrieve Local Evidence with FKF

Use the reviewed [FKF retrieval procedure](references/retrieval.md) for bounded context and exact evidence. Keep base locations, provider configuration, and private operating instructions in the selected base's local instructions.

## Runtime compatibility

1. Inspect the base's instructions and declared runtime before querying. Check `fkf --version` and `fkf context --help` on that executable; the procedure requires `--base`, `--history`, and `--within`. Check `fkf read --help` for base-qualified exact reads.
1. When the global executable differs, use the base's matching locked runtime, such as its existing virtual environment or declared `uv run --frozen` command. Keep the same executable and explicit base throughout the session. Do not upgrade a runtime or migrate a base merely to make a recipe work.
1. If no matching runtime exists, report the mismatch and the unavailable operation. Do not silently substitute older URI, filtering, or base-selection semantics.
1. Follow the retrieval procedure only after this check. Missing indexes, collection, and provider freshness remain explicit boundaries; ordinary retrieval does not authorize repair or collection.

## Provenance and maintenance

The reference is an unchanged MIT-licensed copy of the author's local FKF 7.0.0 candidate skill, reviewed on 2026-09-13. Its digest is recorded above. That candidate skill was not yet published in the upstream repository; this is a reviewed snapshot, not a claim about the latest public release. The installed global FKF 6.0.2 did not support these commands at review time, so check compatibility rather than relying on the version label alone.

Maintain retrieval semantics in FKF first, then review and replace the reference and its digest together. Keep this wrapper limited to global discovery, runtime selection, and provenance.

## Documentation

- [FKF repository](https://github.com/fmind/fkf) · [releases](https://github.com/fmind/fkf/releases)
- [Retrieval procedure](references/retrieval.md)
