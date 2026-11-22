---
name: databricks
description: "Operate Databricks bundles, jobs, pipelines, Unity Catalog, genie."
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

See [genie](references/genie.md) for local `genie` CLI sandbox, profile, layout, compliance, and MCP-secret rules.

## Gotchas

- **Direct bundle engine (CLI 1.20+)**: `bundle.engine: terraform` errors and first deploy migrates state (pin 1.19.x if needed; align local/CI versions).
- **Keyless CI first**: use [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github) (`DATABRICKS_AUTH_TYPE: github-oidc`, `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `id-token: write`), else OAuth M2M (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`); never commit `DATABRICKS_TOKEN`.
- **Ignore `databricks aitools install` hints** (CLI 1.23.0 under Claude Code): preview into a non-discovery `<dir>` via `databricks aitools install --path <dir> --skills <name>` per [vendor-skill policy](../../../agent-harnesses/references/vendor-skills.md).
- **Check cluster autotermination** before starting compute.

## Official Skills

- Upstream: `databricks/databricks-agent-skills` (top-level `skills/`, not `plugins/databricks/`).

## Documentation

- [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli) · [DABs](https://docs.databricks.com/aws/en/dev-tools/bundles) · [Genie Code CLI](https://docs.databricks.com/aws/en/genie-code/genie-code-cli) · [Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog)
- Releases: [Databricks CLI](https://github.com/databricks/cli/releases) · [Genie Code CLI](https://github.com/databricks/genie-code-cli/releases)
- Companions: [sql](../../../sql/SKILL.md), [python](../../../python/SKILL.md).
