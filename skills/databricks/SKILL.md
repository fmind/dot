---
name: databricks
description: "Operate Databricks bundles, jobs, pipelines, Unity Catalog, and Genie Code CLI."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/databricks
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Databricks CLI

Operate DABs, compute, jobs, pipelines, Unity Catalog, and Genie spaces with `databricks`, plus local Data & AI workflows with `genie` (Genie Code CLI).

Pass `--profile <profile>` and `--target <target>` before mutations or billable runs; set `DATABRICKS_BUNDLE_STRICT_PROFILE_MATCH=1` on untrusted bundles (requires `~/.databrickscfg`; omit in CI) because `DATABRICKS_TOKEN` bypasses host matching.

## Workflow

1. **Check profile and caller** (prefer OAuth U2M `databricks auth login --host <url> --profile <profile>`):

   ```bash
   databricks auth profiles --skip-validate
   databricks current-user me --profile <profile>
   ```

1. **Validate, plan, and deploy bundles** (re-plan after edits—`deploy --plan` checks remote drift only—and gitignore `plan.json`):

   ```bash
   databricks bundle validate -t dev -p <profile>
   databricks bundle plan -t dev -p <profile> -o json > plan.json
   databricks bundle deploy -t dev -p <profile> --plan plan.json
   databricks bundle run <job-or-pipeline-key> -t dev -p <profile>
   ```

1. **Inspect Unity Catalog, compute, runs, and Genie** (`--limit` on `list`, CLI 1.25+, avoids full scans):

   ```bash
   databricks catalogs|schemas|tables|clusters get <name-or-id> -p <profile> -o json
   databricks jobs list-runs --job-id <job-id> --limit 10 -p <profile>
   databricks genie list-spaces -p <profile> -o json
   databricks genie ask "QUESTION" -p <profile> -o json
   ```

1. **Gate mutations**: `--target prod`, cluster restarts, ACLs, and schema DDL require approval.

## Genie Code CLI

`genie` uses `databricks` (>= 1.0.0) `~/.databrickscfg` profiles, Unity Catalog, Partner-powered AI, and Unity Gateway (`GENIE_CODE_CLI` in `system.billing.usage`). It loads repo `AGENTS.md`, `.agents/skills/`, `.genie/`, `~/.agents/skills/`, and `$GENIE_HOME/skills/` (default `~/.genie`; bundled skills in `.system/`).

```bash
genie doctor --json
genie exec --json --ephemeral -s read-only -C <dir> "PROMPT"
genie review --uncommitted
```

- **Profile flag**: `genie -p <name>` layers `$GENIE_HOME/<name>.config.toml`, not `~/.databrickscfg` (pick the Databricks profile interactively or set `DATABRICKS_CONFIG_PROFILE`).
- **MCP secrets**: `--env KEY=VAL` writes literals to `config.toml`; register stdio (`genie mcp add <name> -- <cmd> <args...>`) and forward secrets via `env_vars = ["ENV_VAR"]` in `$GENIE_HOME/config.toml` or `with-secret`. Use `--url <url> --bearer-token-env-var ENV_VAR` for HTTP.
- **Sandboxing**: use `-s read-only` or `-s workspace-write` (never `-s danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, or `--dangerously-bypass-hook-trust` on untrusted repos; `genie review` omits `-s`, and `genie exec --ignore-user-config --ignore-rules` isolates untrusted runs).

## Gotchas

- **Direct bundle engine (CLI 1.20+)**: `bundle.engine: terraform` errors and first deploy migrates state (pin 1.19.x if needed; align local/CI versions).
- **Keyless CI first**: use [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github) (`DATABRICKS_AUTH_TYPE: github-oidc`, `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `id-token: write`), else OAuth M2M (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`); never commit `DATABRICKS_TOKEN`.
- **Genie layout & compliance**: `bin/genie` resolves `genie-package.json` for `genie-path/rg` and `genie-resources/` (keep the mise package intact); `--search` is unavailable on compliance-security-profile workspaces.
- **Ignore `databricks aitools install` hints** (CLI 1.23.0 under Claude Code): preview into a non-discovery `<dir>` via `databricks aitools install --path <dir> --skills <name>` per [vendor-skill policy](../agent-project/references/vendor-skills.md).
- **Check cluster autotermination** before starting compute.

## Official Skills

- Upstream: `databricks/databricks-agent-skills` (top-level `skills/`, not `plugins/databricks/`).

## Documentation

- [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli) · [DABs](https://docs.databricks.com/aws/en/dev-tools/bundles) · [Genie Code CLI](https://docs.databricks.com/aws/en/genie-code/genie-code-cli) · [Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog)
- Releases: [Databricks CLI](https://github.com/databricks/cli/releases) · [Genie Code CLI](https://github.com/databricks/genie-code-cli/releases)
- Companions: [duckdb](../duckdb/SKILL.md), [python-stack](../python-stack/SKILL.md).
