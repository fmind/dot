---
name: databricks
description: "Operate Databricks bundles, jobs, pipelines, and Unity Catalog."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/databricks
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Databricks CLI

Operate Databricks workspaces, Declarative Automation Bundles (DABs), clusters, jobs, Lakeflow pipelines, and Unity Catalog with `databricks`.

Always pass `--profile <profile>` and (on bundles) `--target <target>` before mutations or billable runs. Env vars like `DATABRICKS_TOKEN` bypass host-profile matching—set `DATABRICKS_BUNDLE_STRICT_PROFILE_MATCH=1` on untrusted bundles (requires `~/.databrickscfg`, so omit in CI).

## Workflow

1. **Check profile and caller** (prefer OAuth U2M `databricks auth login --host <url> --profile <profile>` over static PATs):

   ```bash
   databricks auth profiles --skip-validate
   databricks current-user me --profile <profile>
   ```

1. **Validate, plan, and deploy bundles** (re-plan after any local edit—`deploy --plan` checks remote drift only—and gitignore `plan.json`):

   ```bash
   databricks bundle validate --target dev --profile <profile>
   databricks bundle plan --target dev --profile <profile> -o json > plan.json
   databricks bundle deploy --target dev --profile <profile> --plan plan.json
   databricks bundle run <job-or-pipeline-key> --target dev --profile <profile>
   ```

1. **Inspect Unity Catalog, compute, and runs** (pass `--limit` on `list`, supported in CLI 1.25+, to avoid full-catalog scans):

   ```bash
   databricks catalogs|schemas|tables|clusters get <name-or-id> --profile <profile> --output json
   databricks jobs list-runs --job-id <job-id> --limit 10 --profile <profile>
   ```

1. **Authorize consequential changes**: `--target prod`, cluster restarts, ACLs, and schema DDL require approval.

## Gotchas

- **Direct bundle engine since CLI 1.20**: `bundle.engine: terraform` errors and first deploy migrates Terraform state (pin 1.19.x if Terraform is still required; align local and CI CLI versions).
- **Keyless CI first**: [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github) in GitHub Actions (`DATABRICKS_AUTH_TYPE: github-oidc`, `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `id-token: write`), else OAuth M2M (`DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`); keep `DATABRICKS_TOKEN` out of repos.
- **Ignore `databricks aitools install` stderr hints** (emitted under Claude Code in CLI 1.23.0 with no opt-out flag): preview skills into a non-discovery `<dir>` via `databricks aitools install --path <dir> --skills <name>` under [vendor-skill policy](../agent-project/references/vendor-skills.md).
- **Check cluster autotermination** before starting compute.

## Official Skills

- Upstream: `databricks/databricks-agent-skills` (select from top-level `skills/`, not `plugins/databricks/`).

## Documentation

- [Databricks CLI guide](https://docs.databricks.com/aws/en/dev-tools/cli) · [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles)
- [Unity Catalog guide](https://docs.databricks.com/aws/en/data-governance/unity-catalog)
- Releases: [Databricks CLI Releases](https://github.com/databricks/cli/releases)
- Companion skills: [duckdb](../duckdb/SKILL.md) (local data), [python-stack](../python-stack/SKILL.md) (Python development).
