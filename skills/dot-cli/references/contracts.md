---
name: contracts
description: "Resolve configuration, JSON output, exit codes, and immutable archive compatibility."
---

# Dot Contracts

Configuration precedence is explicit `--config`, then `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`. A missing default uses built-in defaults; an explicit missing file fails. Workstation policy lives under `auth`, `cache`, and `prune`; `dot config show` exposes the complete defaults. Scope lists replace defaults; native tools own credentials. Configuration uses `schema_version: 3` and positive finite numeric seconds in `timeout_seconds`, `probe_timeout_seconds`, and `stale_lag_seconds`. Unknown keys are rejected. Help and config repair commands remain available with malformed configuration; chezmoi-managed edits go through their source.

Requested data goes to stdout; progress and errors go to stderr. Exit codes are 0 for success, 1 for an operational failure or incomplete result, 2 for usage errors, and 130 for interruption. Public JSON reports have a versioned `schema` envelope; failed operations never become an empty success. Hook protocols retain their host-specific neutral responses and bounded failure evidence.

A generation contains transcript, usage status/measurement, and integrity manifest, published in one atomic directory operation with private permissions. Extraction or publication failure leaves no completed generation. Retry the same ingestion after repairing the cause. The active `sessions/v2` store writes parser 5 with manifest schema 2 and reads parser 3, 4, and 5 bundles. Older admitted parsers remain immutable legacy evidence; explicit recapture creates a parser 5 generation. Earlier stores and standalone usage files remain untouched and are excluded from queries. Compaction compares canonical record fingerprints without retaining the full archive contents in memory; it preserves divergent transcripts, different usage evidence, and fails before deletion on unsupported formats or integrity errors.
