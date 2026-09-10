# Dot CLI

Dot 3 is a typed Python CLI for bounded multi-repository operations, workstation diagnostics, and private agent-session archives. Chezmoi and mise own workstation deployment; skills own AI judgment; native provider CLIs own authentication. The package retains the descriptor-bound filesystem and process-control guarantees of earlier releases.

## Commands and output

| Command                                   | Contract                                                                                                                                                      |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot status [PATH ...]`                   | Read cached Git state and optional Docker status; no fetch. `--json` reports `complete: false` and exits 1 on a repository inspection failure.                |
| `dot pull [PATH ...]`                     | Preview with `--dry-run`; fetch/fast-forward with bounded concurrency otherwise. Dirty worktrees default to skip. `--push` is a separate remote-write opt-in. |
| `dot doctor`                              | Local environment, tools, permissions, services, and install checks. `--deep` also probes provider authentication; `--fix` repairs local file permissions.    |
| `dot config show/path/init/edit/validate` | Inspect and repair strict YAML configuration, including an explicit missing or malformed file.                                                                |
| `dot completion`                          | Generate Fish integration, validate scripts, then atomically replace completion files.                                                                        |
| `dot agent session`                       | Preview, ingest, synchronize, inspect, export, count, and compact immutable session generations.                                                              |
| `dot agent stats`                         | Combine prompt activity, token usage, recorded cost, and offline API equivalents.                                                                             |
| `dot agent usage`                         | List, show, and aggregate selected measurements without invoking providers.                                                                                   |
| `dot agent prompts stats`                 | Count archived user-message activity and lengths without revealing text.                                                                                      |
| `dot agent doctor`                        | Inspect selected integration metadata; `--deep` validates source/archive evidence, and `--explain` adds bounded examples.                                     |
| `dot agent clean`                         | Preview generated project prompts, proposals, and reports; `--apply` removes only those categories.                                                           |

Global flags precede the command. Requested output goes to stdout; diagnostics and progress go to stderr. Exit codes are 0 for success, 1 for operational failure or incomplete results, 2 for invalid CLI usage, and 130 for interruption. Hook responses remain host-specific. JSON diagnostics share `dot.diagnostics/v1` with `scope`, `passed`, and `checks`; optional details remain explicit. Other JSON commands retain their documented versioned payloads. Fish completion comes from the same Typer command definitions as help.

## Configuration

Precedence is `--config`, then `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`. A missing default file means built-in defaults; an explicitly selected missing file is an error. Lists replace defaults; mappings merge with defaults. Unknown fields and coerced scalar types fail validation. Repair commands do not require valid configuration. The optional configuration file is not automatically adopted or overwritten by chezmoi.

```yaml
# Docs: https://github.com/fmind/dot/blob/main/dot/README.md
schema_version: 3
pull:
  directories: [~/work]
  timeout_seconds: 120
  concurrency: 8
doctor:
  probe_timeout_seconds: 45
agent:
  doctor:
    stale_lag_seconds: 86400
```

Use `dot config show` for effective defaults. Timeouts are positive finite numeric seconds. Paths, enabled tools, source roots, concurrency, and diagnostic limits are user choices. Provider scopes, AI prompts, release settings, and cross-tool retention policies are no longer runtime configuration.

## Archive transaction and recovery

```text
~/.agents/sessions/v1/<agent>/<lineage>/<generation>/
  manifest.json
  transcript.jsonl
  usage.json
```

Parser 3 writes manifest schema 2. The manifest binds transcript and usage digests to a source fingerprint and parser version. Usage is explicitly available or unsupported. Failed usage extraction is an operation failure, recorded by the invoking hook when applicable; it never publishes a completed generation. Each file is private (`0o600`), each directory is private (`0o700`), and publication stages and validates the whole bundle before one atomic directory rename. Failed publication is safe to retry; concurrent duplicates validate the existing bundle rather than overwrite it.

File adapters parse captured bytes. Copilot reads turns and usage inside one read transaction. Grok includes both captured transcript and signals bytes in generation identity, so changed usage cannot disappear behind an unchanged transcript. Signals-only sessions can preserve usage without transcript records. A source that changes creates a distinct generation; no old generation is rewritten.

Usage queries choose one measurement per session from the latest supported bundle. They read legacy standalone usage only for sessions without a bundle and never sum retained generations. Unsupported usage in a new bundle is not replaced with an older measurement. Unknown costs are null; provider-reported, estimated, and context-only measurements remain separate.

Compaction is preview-first and revalidates before deletion. It compares canonical record fingerprints so full transcript content is retained for only one generation at a time. It retains divergent histories, distinct usage evidence, unknown formats, and separate parser generations. Dot does not delete provider-owned session files or unrelated tool caches. Backups and source retention are separate explicit operations.

## Version 2 migration

1. Preserve the existing configuration and archives before upgrading an installed runtime. The rewrite does not migrate a live store or apply workstation changes automatically.
1. Replace obsolete commands using the table below. Update external scripts that consume diagnostic JSON or usage-error exit codes.
1. Replace the retired `git g` alias with the conventional-commit skill or native `git commit`; the managed Git configuration removes the alias on the next authorized apply.
1. Update configuration: use `schema_version: 3`, rename `verify` to `doctor`, and replace duration strings with numeric `timeout_seconds`, `probe_timeout_seconds`, and `stale_lag_seconds` fields. Move `login.github_host` to `doctor.github_host`. Remove the retired `ai`, `commit`, `pr`, `release`, `login`, `setup`, `prune`, and `chezmoi_clean` sections after retaining any policy still needed in its owning skill or provider setup.
1. Run `dot config validate`, then preview `dot agent session sync --dry-run --json`. To migrate retained raw sources, run the same command without `--dry-run`; successful sessions create new generations and failures remain retryable. Missing raw sources remain legacy evidence and cannot be reconstructed from normalized transcripts.
1. Inspect session, usage, and integration results. Keep the old generations and raw sources through acceptance. Deployment rollback can select the prior runtime, but older clients do not understand schema-2 bundles; preserve the pre-upgrade snapshot for a complete data rollback.

| Retired runtime command       | Owner or replacement                                                                                                    |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `dot verify`                  | `dot doctor`; provider authentication probes now require `--deep`.                                                      |
| `dot commit`                  | The conventional-commit skill and staged `git commit`.                                                                  |
| `dot pr` / `dot pull-request` | The github-pull-request skill and reviewed `gh pr create/edit`.                                                         |
| `dot login` / `dot setup`     | Scoped `mise run login:<provider>` and `mise run setup:<provider>` tasks below.                                         |
| `dot release`                 | `mise run release -- [OPTIONS]` in this repository.                                                                     |
| `dot prune`                   | `mise run prune` for local tool caches; `dot agent session compact` and `dot agent clean` for owned archives/artifacts. |
| `dot chezmoi clean`           | Explicit inspection and recovery of retired managed links through the chezmoi and dot-skills guidance.                  |
| `dot agent usage sync`        | `dot agent session sync`, the single transcript/usage write path.                                                       |

## Scoped authentication and setup

After chezmoi applies the configuration, the login/setup tasks are available from any directory. Their source is [`dot_config/mise/conf.d/maintenance.toml`](../dot_config/mise/conf.d/maintenance.toml), deployed to `~/.config/mise/conf.d/maintenance.toml`. The `[vars]` section retains the prior scope policy: `github_scopes`, `workspace_scopes`, and `workspace_apis`. Both GitHub tasks share the same list; Workspace login requests its explicit list rather than a provider's changing default. These tasks run only when invoked, use the caller's current directory, and use the providers' native interactive authentication. A project task with the same name can override a global task. Repository build and release tasks remain local.

| Task                                     | Behavior                                                                                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mise run login:github`                  | GitHub login with the configured scopes. Select another host with `--host` or `GH_HOST`.                                                              |
| `mise run setup:github`                  | Refresh those scopes for the active account, or log in if unauthenticated. Supports the same host selection.                                          |
| `mise run login:gcp`                     | Google Cloud login plus ADC, retaining `--update-adc`.                                                                                                |
| `mise run login:workspace`               | Workspace login with the configured scopes and the selected native gws profile.                                                                       |
| `mise run setup:workspace -- PROJECT_ID` | Enable the configured Workspace APIs in that project, then run native OAuth setup. `GWS_PROJECT` can supply the project when the argument is omitted. |

Select the intended native account/configuration before setup; `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` selects a separate gws profile. Workspace setup enables cloud APIs, so invoke it for a project you intend to modify. For application defaults and basic provider authentication, see the [root setup guide](../README.md#authentication--logins).

## Global cache cleanup

Run `mise run prune` (or `mise run mp`) from any directory to clean the local tool caches below. Use `mise run --dry-run prune` to inspect the commands first; this is a command preview, not an estimate of reclaimable bytes. Each task calls its tool's supported cache operation and propagates failures.

| Task           | Operation                                                                                                          |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| `prune:uv`     | Prune unused package entries and cached environments with `uv cache prune`; retain uv's in-use protection.         |
| `prune:npm`    | Garbage-collect unneeded entries and check integrity with `npm cache verify`.                                      |
| `prune:mise`   | Clear metadata/task caches with `mise cache clear`; retain installed tool versions.                                |
| `prune:dprint` | Clear downloaded plugins and formatting cache with `dprint clear-cache`. Plugins are downloaded again when needed. |
| `prune:trivy`  | Clear scan results with `trivy clean --scan-cache`; retain vulnerability databases and checks.                     |

Docker build cache and Hugging Face model/data revisions have separate interactive tasks: `mise run prune:docker` uses the selected Docker builder; `mise run prune:hf` shows detached revisions before confirmation. Neither runs in the default aggregate. To combine either with routine cleanup, use `mise run prune ::: prune:docker` or `mise run prune ::: prune:hf`. Installed tools, credentials, provider session files, and Dot archives are outside the cache aggregate. The repository-only `mise run prune:sessions` preserves the earlier archive-compaction preview; apply compaction explicitly through the Dot CLI.

## Implementation and validation

`src/fmind_dot/agent.py` defines command contracts; `archive/` owns parsing, ingestion, immutable storage, and projections. `agent_doctor.py` owns integration evidence, `hooks.py` owns host payloads and failure records, and `artifacts.py` owns generated-file cleanup. `state.py`, `process.py`, and `private_files.py` provide the shared execution and filesystem boundaries. `system.py` owns workstation integration. Repository-only release, skill validation, and tool audits live in `dot_tasks/` and are excluded from the wheel. Markdown parsing is a development dependency.

The hashed two-slot installer remains: it builds from the selected source, installs the exact runtime dependency graph, verifies the receipt and executable, and atomically selects the runtime. Build invalidation and installation freshness include the bundled pricing YAML as well as Python modules. A plain tool install would not provide all of those guarantees. Installed-runtime proof is separate from source checks.

Run `mise run all` for formatting, static checks, tests, and builds. Linux runs the full gate; the macOS CI job runs Python checks, behavioral tests (including process groups, archive races, and installation), and packaging. Hosted execution is proven only after CI runs for the reviewed commit. The starter smoke task remains an explicit additional check.

## Agent statistics

```bash
dot agent session sync
dot agent stats --since 7d --by-model
dot agent stats --agent codex --project . --json
dot agent usage stats --by-model --by-project
dot agent prompts stats --since 2026-09-01 --json
```

`stats` reads local archives without calling a provider or printing prompt text. Prompt counts are archived user messages (including injected context), distinct from assistant turns and API requests. Token totals retain their measurement kind: provider-reported, estimated, context-only, or unknown. Different kinds are never summed together. Prompt dates use conversation timestamps; usage dates select whole sessions at their recorded timestamp. Combined-report dates are inclusive exact UTC instants (a bare date means midnight); durations such as `7d` and `24h` are accepted. These counts describe captured evidence, not every interaction with an account. Prompt and combined statistics return usable partial results with `complete: false` and exit 1 when legacy or partial sessions prevent complete coverage; archive migration remains an explicit operation. Run session sync to refresh supported adapters; Cursor history capture is not yet supported, so Cursor activity is absent rather than estimated from invented records.

The `api_equivalent_usd` estimate is separate from recorded `cost_usd`. The bundled rate card uses standard short-context USD prices verified on 2026-09-10, with 5-minute cache writes. It excludes long-context premiums, priority/fast processing, regional and tool fees, taxes, subscriptions and discounts; it applies those rates even to older sessions. Session totals cannot reconstruct per-request context lengths or cache lifetimes. See the [OpenAI rate card](https://developers.openai.com/api/docs/pricing) and [Claude rate card](https://platform.claude.com/docs/en/about-claude/pricing). This is a comparison estimate, not an invoice.

`priced_sessions`, `pricing_complete` and `unpriced_reasons` expose price coverage. Unknown/mixed models, unverified accounting, unsupported cache writes and missing rates remain unpriced (`null`), while known zero remains zero. Model matching is exact; add an explicit alias or newer model through `agent.pricing.models` in the Dot YAML configuration. Override `as_of`, `basis` and `sources` when supplying a different rate card. Rates are USD per million tokens; the packaged defaults and effective overrides are visible through `dot config show`.

```yaml
agent:
  pricing:
    as_of: "2026-09-10"
    models:
      gpt-5.4:
        input: 2.5
        output: 15.0
        cache_read: 0.25
```
