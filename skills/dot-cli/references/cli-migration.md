# CLI Migration

These changes follow Dot 5.2.0. Update scripts before deploying this checkout; archived files and their schemas do not change.

## Commands

| Previous command                | Replacement                                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `dot login all`                 | `dot login google` authenticates Workspace, then Google Cloud and ADC. GitHub remains `dot login github`. |
| `dot agent usage stats`         | `dot agent stats --tokens-only`                                                                           |
| `dot agent prompts stats`       | `dot agent stats --prompts-only`                                                                          |
| `dot agent clean`               | Removed. Review and manage retained project documents explicitly.                                         |
| `dot status` Docker section     | `dot doctor` for Docker health; `dot cache docker` for space usage.                                       |
| `dot --verbose` / `DOT_VERBOSE` | Removed; native provider tools own detailed diagnostics.                                                  |

The two old report routes (`dot agent usage stats` and `dot agent prompts stats`) are removed and exit 2; use `dot agent stats --tokens-only` or `--prompts-only`. Session storage health remains under `dot agent session stats`; usage record inspection remains under `dot agent usage list` and `show`.

Use `--agent` consistently; `--harness` and `-a` remain filter aliases. Both list commands accept `--limit 0` for all rows and reject negative limits. Global options precede the command.

## Date boundaries and errors

Date-only `--since` begins at midnight UTC; date-only `--until` includes the whole UTC day. Explicit timestamps retain their exact boundary. Duration filters such as `7d` and `24h` are accepted across date-filtered commands. Timestamp sources remain distinct: source modification for sync, ingestion for session queries, conversation events for prompt statistics, and request or session timestamps for usage statistics.

Help works even with missing or malformed configuration. Commands still validate configuration before inspecting or changing state. Invalid command inputs exit 2; configuration, provider, and incomplete-result failures exit 1. Failed fetches remain failures even without an upstream branch.

## JSON selectors

Public JSON reports use a top-level `schema` field. Update selectors as follows; warnings and errors remain on stderr. A failure before report construction may produce no JSON, so always check the exit status.

| Command                         | Schema                      | Data selector                                                    |
| ------------------------------- | --------------------------- | ---------------------------------------------------------------- |
| `dot pull --json`               | `dot.pull/v1`               | `.repositories[]` instead of `.[]`; `.complete` records success. |
| `dot pull --dry-run --json`     | `dot.pull.plan/v1`          | `.repositories[]` (unchanged).                                   |
| `dot status --json`             | `dot.status/v1`             | `.repositories[]`; `.docker` is removed.                         |
| `dot status --stats --json`     | `dot.status.stats/v1`       | Top-level counts (unchanged).                                    |
| `dot agent session list --json` | `dot.agent.session.list/v1` | `.sessions[]` instead of `.[]`.                                  |
| `dot agent session show`        | `dot.agent.session.show/v1` | `.session` instead of the root object.                           |
| `dot agent usage list --json`   | `dot.agent.usage.list/v1`   | `.records[]` instead of `.[]`.                                   |
| `dot agent usage show`          | `dot.agent.usage.show/v1`   | `.record` instead of the root object.                            |
| `dot agent stats --json`        | `dot.agent.stats/v2`        | `.prompts` and `.usage[]` (unchanged).                           |

Token-only reports set `prompts` to `null`; prompt-only reports leave `usage` empty. Session export, sync, storage statistics, and diagnostics retain their existing envelopes. Native cache/provider output and internal host hook protocols retain their native formats.
