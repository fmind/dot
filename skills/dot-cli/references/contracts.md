---
name: contracts
description: "Resolve configuration, JSON output, exit codes, and session archive compatibility."
---

# Dot Contracts

Configuration precedence is explicit `--config`, then `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`. A missing default uses built-in defaults; an explicit missing file fails. Workstation policy lives under `auth`, `cache`, and `prune`; `dot config show` exposes the complete defaults. Scope lists replace defaults; native tools own credentials. Configuration uses `schema_version: 3` and positive finite numeric seconds in `timeout_seconds`, and `probe_timeout_seconds`. Unknown keys are rejected. Help and config repair commands remain available with malformed configuration; chezmoi-managed edits go through their source.

Requested data goes to stdout; progress and errors go to stderr. Exit codes are 0 for success, 1 for an operational failure or incomplete result, 2 for usage errors, and 130 for interruption. Public JSON reports have a versioned `schema` envelope; failed operations never become an empty success. Notification hooks always exit 0 and report a failure as one stderr line.

The active `sessions/v3` store keeps one private bundle per agent session, `<agent>/<session_id>.jsonl`: a manifest line (schema 3) with provenance, counts, source signature, and usage, then the normalized records. Sync serializes writers with an owner-only `.write.lock` and replaces the whole file atomically, only when the new parse has at least as many records and its usage extraction succeeded; otherwise it keeps the archived copy and reports the failure. Sync writes parser 5 and reads parser 3, 4, and 5 bundles; parsers 3 and 4 come only from the v2 migration and are flagged as legacy until sync recaptures their sources. The first archive access migrates `sessions/v2` (most records, newest on ties, with the newest available usage) without modifying it; earlier stores and standalone usage files are never read. Unsupported formats fail queries and sync before any change.
