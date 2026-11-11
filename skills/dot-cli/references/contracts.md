---
name: contracts
description: "Resolve configuration, JSON output, exit codes, and session archive compatibility."
---

# Dot Contracts

Config precedence: `--config` → `DOT_CONFIG_PATH` → `~/.config/dot.yaml` (missing default uses built-ins; explicit missing path fails). `dot config show` prints `schema_version: 3` defaults (`agent`, `auth`, `cache`, `completions`, `doctor`, `privacy`, `prune`, `pull`, `trust`, including machine-local `privacy.allowed_tokens` for already-public tokens never named in the repo); scope lists replace defaults, native CLIs own credentials, and timeouts/concurrency/secret modes are fixed in code. Unknown keys (including removed settings or retired/misspelled `agent.sources`) fail with their key path; fix via `dot config edit` (`--help` and config repair still work when malformed).

Stdout carries requested data; stderr carries progress, prompts, and errors. Exit codes: `0` success, `1` operational failure or incomplete result, `2` usage error (including unknown agents or zero durations like `0d`; `7d`/`24h` work across date filters per [daily workflows](daily-workflows.md)), `130` interruption (stopping child processes, including during startup). JSON reports use a versioned `schema` envelope (indented on TTY, compact when piped) and never turn failures into empty success. `orphan` and `secret` ignore config; notify hooks read only `agent.notify` (falling back to defaults with one stderr line on bad config) and always exit `0`.

## JSON selectors

Always check exit status: pre-report failures emit no JSON, and warnings stay on stderr.

| Command                             | Schema                        | Data selector                                                                                                                                                                                             |
| ----------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot pull --json`                   | `dot.pull/v1`                 | `.repositories[]`; `.complete` records success.                                                                                                                                                           |
| `dot pull --dry-run --json`         | `dot.pull.plan/v1`            | `.repositories[]`                                                                                                                                                                                         |
| `dot status --json`                 | `dot.status/v1`               | `.repositories[]` (`needs_attention`), top-level `complete` (`false` on inspection failure), `needs_attention`, `remote_state` (`fetched` with `--fetch`).                                                |
| `dot agent session list --json`     | `dot.agent.session.list/v2`   | `.sessions[]` with `parser_version`.                                                                                                                                                                      |
| `dot agent session show`            | `dot.agent.session.show/v2`   | `.session`; `--content` adds `.records[]`, bounded by `--role` and `--tail`.                                                                                                                              |
| `dot agent session sync --json`     | `dot.agent.session.sync/v2`   | Counts `selected`, `ingested`, `unchanged`, `retained`, `retained_current_transcripts`, `skipped`, `failed`; stderr prints per-agent summaries and retained lines (`--verbose` adds ingested), never IDs. |
| `dot agent stats --sessions --json` | `dot.agent.stats.sessions/v1` | `.records[]`, one usage record per session, newest activity first.                                                                                                                                        |
| `dot orphan --json`                 | `dot.orphan/v1`               | `.targets[]`                                                                                                                                                                                              |
| `dot cache --json`                  | `dot.cache/v1`                | `.providers[]` (`name`, `command`, native `report` / `error` / `skipped`); `--dry-run` lists commands only.                                                                                               |
| `dot trust --json`                  | `dot.trust/v1`                | `.folders[]` (`path`, `changed`), `.skipped[]`, `.harnesses`, `.agy_projects[]`, `.claude_directories[]`; supports multiple targets and `--dry-run`.                                                      |
| `dot agent stats --json`            | `dot.agent.stats/v4`          | `.prompts` (`null` on token-only), `.usage[]` (empty on prompt-only), `.pricing` (`as_of`, `basis`, `sources`), `.time_basis` (both `null` on `--prompts-only`).                                          |

Diagnostics use `dot.diagnostics/v1`; `agent doctor` carries `agent`, `hooks`, `source`, `last_sync`, `sync_failures`, `sync_retained`, `archive`, `sessions`, `healthy`, `next`, `discovery` (`ok` or `broken:` naming `persona`/`skills`), and advisory `note` (e.g. missing `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, which makes OpenCode load skills twice without failing `healthy`). Stats `retained_usage_sessions` marks sessions keeping usage from an earlier smaller capture, setting `usage_complete` and `cost_complete` false. `dot login <provider> --check` prints `provider: ready | login needed | unknown (...)` and exits 1 unless all are ready.

## Session archive

`~/.agents/sessions/v3/<agent>/<session_id>.jsonl` stores manifest, usage, and transcript lines. Sync writes parser 15, reads all earlier released parsers (marking older captures `legacy` until recaptured; retired Codex and Grok stay `legacy`), and upgrades schema 3 bundles in place without content changes.

Sync writes atomically and never overwrites a bundle with fewer records, shorter matching messages, lost usage/known cost, or stale competing writes: those count as `retained` (`retained == retained_current_transcripts` proves zero transcript loss) and retry next sync. Malformed JSONL or usage-extraction errors count as `failed` without replacing archived data. Missing measurements stay unavailable; explicit zeros stay `0`.

Subagent transcripts carry `sidechain` and `parent_session_id`. Claude `isMeta` user turns set `"meta": true` (omitted when false or in older captures). Older stores (`sessions/v2`) are ignored (delete manually), unsupported bundles fail queries without replacement, and unexpandable `~user` paths exit 2. See [session compatibility](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/references/session-compatibility.md) and [provider measurement](agent-usage.md#provider-measurement).
