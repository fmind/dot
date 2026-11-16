---
name: contracts
description: "Resolve configuration, JSON output, exit codes, and session archive compatibility."
---

# Dot Contracts

Config precedence: `--config` → `DOT_CONFIG_PATH` → `~/.config/dot.yaml` (missing default uses built-ins; explicit missing path fails). Defaults use `schema_version: 3` (`auth`, `pull`, `trust`, `privacy`, backed by bundled `policy.yaml` scope catalogs and machine-local `privacy.allowed_tokens`); `auth.workspace.extra_scopes` extends bundled Workspace scopes (up to 50 total), native CLIs own credentials, and unknown/retired keys fail with their key path (`--help` and `doctor --headroom` still work when malformed).

Stdout carries requested data; stderr carries progress, prompts, and errors. Exit codes: `0` success, `1` operational failure or incomplete result, `2` usage error (including unknown agents or zero durations like `0d`), `130` interruption. JSON reports use a versioned `schema` envelope (indented on TTY, compact when piped) and never turn pre-report failures into empty success. `doctor --headroom` ignores config.

## JSON selectors

| Command              | Schema               | Data selector                                                                                                                                                                                                     |
| -------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot doctor --json`  | `dot.diagnostics/v1` | `.checks[]` (`name`, `status`, `group`, optional `condition`, `path`, `details`), `.passed`.                                                                                                                      |
| `dot pull --json`    | `dot.pull/v1`        | `.repositories[]`; `.complete` records success.                                                                                                                                                                   |
| `dot status --json`  | `dot.status/v1`      | `.repositories[]` (`needs_attention`), top-level `complete`, `needs_attention`, `remote_state` (`fetched` on `--fetch`).                                                                                          |
| `dot context --json` | `dot.context/v5`     | `.budgets.{global,local}`, `.totals`, `.duplicates`, `.passed`.                                                                                                                                                   |
| `dot stats --json`   | `dot.stats/v5`       | `.coverage`, `.usage[]`, `.pricing` (`as_of`, `basis`, `sources`), and optional `.sync` (`failed`, `retained`, `retained_current_transcripts`; stderr hides IDs, exits `1` after writing output if `failed > 0`). |

`dot login <provider> --check` prints `provider: ready | login needed | unknown (...)` and exits `1` unless all are ready.

## Session archive

`~/.agents/sessions/v3/<agent>/<session_id>.jsonl` stores manifest (`schema_version` 4), usage, and transcript lines. Sync writes parser 16 atomically and reads released parsers 7–16 (keeping older captures and retired `codex`, `copilot`, `grok`, and `opencode` archives queryable).

Sync never overwrites a bundle with fewer records or lost usage/known cost: those count as `retained` (`retained == retained_current_transcripts` proves zero transcript loss) and retry next sync; malformed sources count as `failed` without replacing archived data. Subagent transcripts carry `sidechain` and `parent_session_id`; Claude `isMeta` user turns set `"meta": true`. Older stores (`sessions/v2`) are ignored, unsupported bundles fail queries, and unexpandable `~user` paths exit `2`. See [session compatibility](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/references/session-compatibility.md) and [provider measurement](agent-usage.md#provider-measurement).
