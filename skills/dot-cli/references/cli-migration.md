# CLI Migration

These changes follow Dot 5.2.0; the session archive changes follow Dot 6.3.2. Update scripts before deploying this checkout. Dot 7.0.4 is the last release that migrates `~/.agents/sessions/v2` into `v3`: later releases refuse a store that exists only as `v2` and name the migrating release, never modifying `v2`. Remove `v2` after verifying the new store. Managed harness hooks now only notify: apply them so no harness calls a removed capture hook.

## Commands

| Previous command                                  | Replacement                                                                                               |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `dot login all`                                   | `dot login google` authenticates Workspace, then Google Cloud and ADC. GitHub remains `dot login github`. |
| `dot agent usage stats`                           | `dot agent stats --tokens-only`                                                                           |
| `dot agent prompts stats`                         | `dot agent stats --prompts-only`                                                                          |
| `dot agent clean`                                 | Removed. Review and manage retained project documents explicitly.                                         |
| `dot status` Docker section                       | `dot doctor` for Docker health; `dot cache docker` for space usage.                                       |
| `dot --verbose` / `DOT_VERBOSE`                   | Removed; native provider tools own detailed diagnostics.                                                  |
| `dot agent session compact`                       | Removed: the store keeps one copy per session. `mise run prune:sessions` is removed too.                  |
| `dot agent session ingest`                        | `dot agent session sync --agent <agent> --session <id>`                                                   |
| `dot agent hook session`                          | Removed with its harness hooks; `dot agent session sync`, which `stats` and `usage` run first.            |
| `dot agent hook copilot-session-end`              | Removed; sync reads `~/.copilot/session-store.db` directly.                                               |
| `dot agent doctor --fix`/`--dry-run`              | `chezmoi diff` and `chezmoi apply --force` on the named hook configuration.                               |
| `dot agent doctor --deep`/`--explain`             | Removed; the doctor reports notify hooks, last sync, and archive readability per agent.                   |
| `session list --all-generations`, `show --latest` | Removed; one copy per session. Statuses are `current`, `partial`, `legacy`, `invalid`.                    |

The two old report routes (`dot agent usage stats` and `dot agent prompts stats`) are removed and exit 2; use `dot agent stats --tokens-only` or `--prompts-only`. Session storage health remains under `dot agent session stats`; usage record inspection remains under `dot agent usage list` and `show`.

Use `--agent` consistently; `--harness` and `-a` remain filter aliases. Both list commands accept `--limit 0` for all rows and reject negative limits. Global options precede the command.

## Date boundaries and errors

Date-only `--since` begins at midnight UTC; date-only `--until` includes the whole UTC day. Explicit timestamps retain their exact boundary. Duration filters such as `7d` and `24h` are accepted across date-filtered commands. Timestamp sources remain distinct: source modification for sync, ingestion for session queries, conversation events for prompt statistics, and request or session timestamps for usage statistics.

Help works even with missing or malformed configuration. Commands still validate configuration before inspecting or changing state. Invalid command inputs exit 2; configuration, provider, and incomplete-result failures exit 1. Failed fetches remain failures even without an upstream branch.

## JSON selectors

Public JSON reports use a top-level `schema` field. Update selectors as follows; warnings and errors remain on stderr. A failure before report construction may produce no JSON, so always check the exit status.

| Command                          | Schema                        | Data selector                                                                |
| -------------------------------- | ----------------------------- | ---------------------------------------------------------------------------- |
| `dot pull --json`                | `dot.pull/v1`                 | `.repositories[]` instead of `.[]`; `.complete` records success.             |
| `dot pull --dry-run --json`      | `dot.pull.plan/v1`            | `.repositories[]` (unchanged).                                               |
| `dot status --json`              | `dot.status/v1`               | `.repositories[]`; `.docker` is removed.                                     |
| `dot status --stats --json`      | `dot.status.stats/v1`         | Top-level counts (unchanged).                                                |
| `dot agent session list --json`  | `dot.agent.session.list/v2`   | `.sessions[]`; no `lineage_id`/`generation_id`, adds `parser_version`.       |
| `dot agent session show`         | `dot.agent.session.show/v2`   | `.session`; same fields as list.                                             |
| `dot agent session export`       | `dot.agent.sessions/v2`       | `.sessions[]` (JSON) or `.session` (NDJSON); same fields as list.            |
| `dot agent session sync --json`  | `dot.agent.session.sync/v2`   | Counts `selected`, `ingested`, `unchanged`, `retained`, `skipped`, `failed`. |
| `dot agent session stats --json` | `dot.agent.sessions.stats/v2` | No `generations`/`superseded_generations`.                                   |
| `dot agent usage list --json`    | `dot.agent.usage.list/v1`     | `.records[]` instead of `.[]`.                                               |
| `dot agent usage show`           | `dot.agent.usage.show/v1`     | `.record` instead of the root object.                                        |
| `dot agent stats --json`         | `dot.agent.stats/v2`          | `.prompts` and `.usage[]` (unchanged).                                       |

Token-only reports set `prompts` to `null`; prompt-only reports leave `usage` empty. Diagnostics retain the `dot.diagnostics/v1` envelope; agent doctor details now carry `hooks`, `source`, `last_sync`, `sync_failures`, `archive`, `sessions`, and `next`. The `agent.doctor` and `agent.hook_failures` configuration keys are removed; delete them from custom configuration files, and delete `~/.agents/hook-failures` once no longer needed. Native cache/provider output and internal host hook protocols retain their native formats.

## Credentials

Shell startup no longer exports API keys. Native HF, Kaggle, and OpenCode logins are seeded only when absent; remaining personal keys use `dot secret run NAME -- COMMAND`. Use `dot secret publish` for the PyPI token. Apply and reinstall together, then restart from a clean login session; existing processes retain previously exported keys. Follow [secret setup and account overrides](../../../README.md#secret-management).
