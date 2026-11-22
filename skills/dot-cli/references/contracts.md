---
name: contracts
description: "Resolve configuration, JSON output, and exit codes."
---

# Dot Contracts

Config precedence: `--config` → `DOT_CONFIG_PATH` → `~/.config/dot.yaml` (missing default uses built-ins; explicit missing path fails). Defaults use `schema_version: 3` (`auth`, `pull`, `trust`, `privacy`, backed by bundled `policy.yaml` scope catalogs and machine-local `privacy.allowed_tokens`); `auth.workspace.extra_scopes` extends bundled Workspace scopes (up to 50 total), native CLIs own credentials, and unknown/retired keys fail with their key path (`--help` and `doctor --headroom` still work when malformed).

Stdout carries requested data; stderr carries progress, prompts, and errors. Exit codes: `0` success, `1` operational failure or incomplete result, `2` usage error, `130` interruption. JSON reports use a versioned `schema` envelope (indented on TTY, compact when piped) and never turn pre-report failures into empty success. `doctor --headroom` ignores config.

## JSON selectors

| Command              | Schema               | Data selector                                                                                                                                                                                                                                                       |
| -------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot doctor --json`  | `dot.diagnostics/v1` | `.checks[]` (`name`, `status`, `group`, optional `condition`, `path`, `details`; `-q` keeps `fail`/`warn`), `.passed`.                                                                                                                                              |
| `dot pull --json`    | `dot.pull/v1`        | `.repositories[]`; `.complete` records success.                                                                                                                                                                                                                     |
| `dot status --json`  | `dot.status/v1`      | `.repositories[]` (`needs_attention`), top-level `complete`, `needs_attention`, `remote_state` (`fetched` on `--fetch`).                                                                                                                                            |
| `dot context --json` | `dot.context/v6`     | `.budgets.{global,local}`, `.subagent_budgets.{global,local}`, `.totals`, `.duplicates`, `.duplicate_subagents`, `.passed` (`-q` emits only `schema`, `passed`, `budgets`, `subagent_budgets`, `duplicates`, `duplicate_subagents`; `--quiet --details` exits `2`). |
| `dot privacy --json` | `dot.privacy/v1`     | `.targets[]` (`path`, `passed`, `findings`; `-q` keeps failing targets), `.passed`.                                                                                                                                                                                 |

`dot login <provider> --check` prints `provider: ready | login needed | unknown (...)` and exits `1` unless all are ready.
