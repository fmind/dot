---
name: contracts
description: "Resolve configuration, JSON output, exit codes, and session archive compatibility."
---

# Dot Contracts

Config precedence: `--config` → `DOT_CONFIG_PATH` → `~/.config/dot.yaml` (missing default uses built-ins; explicit missing path fails). `dot config show` prints `schema_version: 3` defaults (`agent`, `auth`, `cache`, `completions`, `doctor`, `privacy`, `prune`, `pull`, `trust`, including machine-local `privacy.allowed_tokens`); scope lists replace defaults, native CLIs own credentials, and unknown/retired keys fail with their key path (`dot config edit` and `--help` still work when malformed).

Stdout carries requested data; stderr carries progress, prompts, and errors. Exit codes: `0` success, `1` operational failure or incomplete result, `2` usage error (including unknown agents or zero durations like `0d`), `130` interruption. JSON reports use a versioned `schema` envelope (indented on TTY, compact when piped) and never turn pre-report failures into empty success. `orphan` and `secret` ignore config. Managed `EDITOR="$HOME/.local/bin/nvim-tty"` executes `nvim` on TTY stdin/stdout and fails closed (exit `1`) in non-TTY agent shells rather than hanging.

## JSON selectors

| Command                             | Schema                        | Data selector                                                                                                            |
| ----------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `dot pull --json`                   | `dot.pull/v1`                 | `.repositories[]`; `.complete` records success.                                                                          |
| `dot pull --dry-run --json`         | `dot.pull.plan/v1`            | `.repositories[]`                                                                                                        |
| `dot status --json`                 | `dot.status/v1`               | `.repositories[]` (`needs_attention`), top-level `complete`, `needs_attention`, `remote_state` (`fetched` on `--fetch`). |
| `dot agent session list --json`     | `dot.agent.session.list/v2`   | `.sessions[]` with `parser_version`.                                                                                     |
| `dot agent session show`            | `dot.agent.session.show/v2`   | `.session`; `--content` adds `.records[]` (`--role`, `--tail`).                                                          |
| `dot agent session sync --json`     | `dot.agent.session.sync/v2`   | `selected`, `ingested`, `unchanged`, `retained`, `retained_current_transcripts`, `skipped`, `failed` (stderr hides IDs). |
| `dot agent stats --sessions --json` | `dot.agent.stats.sessions/v1` | `.records[]`, one usage record per session, newest activity first.                                                       |
| `dot orphan --json`                 | `dot.orphan/v1`               | `.targets[]`                                                                                                             |
| `dot cache --json`                  | `dot.cache/v1`                | `.providers[]` (`name`, `command`, `report` / `error` / `skipped`).                                                      |
| `dot trust --json`                  | `dot.trust/v1`                | `.folders[]` (`path`, `changed`), `.skipped[]`, `.harnesses`, `.agy_projects[]`, `.claude_directories[]`.                |
| `dot agent stats --json`            | `dot.agent.stats/v4`          | `.prompts`, `.usage[]`, `.pricing` (`as_of`, `basis`, `sources`), `.time_basis` (null on `--prompts-only`).              |

Diagnostics use `dot.diagnostics/v1` (`agent doctor` reports `agent`, `source`, `last_sync`, `sync_failures`, `sync_retained`, `archive`, `sessions`, `healthy`, `next`, `discovery`, and advisory `note`). `retained_usage_sessions` marks sessions keeping usage from an earlier smaller capture (`usage_complete: false`, `cost_complete: false`). `dot login <provider> --check` prints `provider: ready | login needed | unknown (...)` and exits `1` unless all are ready.

## Session archive

`~/.agents/sessions/v3/<agent>/<session_id>.jsonl` stores manifest (`schema_version` 4; schema 3 remains readable), usage, and transcript lines. Sync writes parser 15 atomically and reads all earlier released parsers (marking older captures and retired `codex`/`grok` `legacy`).

Sync never overwrites a bundle with fewer records, shorter matching messages, lost usage/known cost, or stale competing writes: those count as `retained` (`retained == retained_current_transcripts` proves zero transcript loss) and retry next sync; malformed sources count as `failed` without replacing archived data. Subagent transcripts carry `sidechain` and `parent_session_id`; Claude `isMeta` user turns set `"meta": true`. Older stores (`sessions/v2`) are ignored, unsupported bundles fail queries, and unexpandable `~user` paths exit `2`. See [session compatibility](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/references/session-compatibility.md) and [provider measurement](agent-usage.md#provider-measurement).
