---
name: databricks
description: "Operate Databricks bundles, jobs, pipelines, and Unity Catalog with databricks."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/databricks
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Databricks CLI

Use `databricks` for Databricks workspace management, Asset Bundles (DABs), compute clusters, jobs, Lakeflow pipelines, and Unity Catalog data governance.

Resolve the workspace, profile, and bundle target before mutations; deployments and runs can incur costs and need authorization. Pass `--profile <profile>` consistently.

## Workflow

1. **Verify workspace and authentication**: list configured profile names without printing credentials and confirm caller identity.

   ```bash
   databricks auth profiles
   databricks current-user me --profile <profile>
   ```

1. **Authenticate via OAuth**: use browser-based OAuth user-to-machine (U2M) login; avoid static personal access tokens.

   ```bash
   databricks auth login --host <workspace-url>
   ```

1. **Validate and deploy Asset Bundles (DABs)**: validate bundle structure before deploying to an isolated target.

   ```bash
   databricks bundle validate --target dev
   databricks bundle deploy --target dev
   databricks bundle run <job-or-pipeline-key> --target dev
   ```

1. **Inspect Unity Catalog assets**: list catalogs, schemas, and tables with bounded read calls.

   ```bash
   databricks catalogs list
   databricks schemas list <catalog>
   databricks tables list <catalog> <schema>
   ```

1. **Inspect compute and job runs**: check cluster state and recent job executions before scheduling changes.

   ```bash
   databricks clusters list --output json
   databricks jobs list-runs --job-id <job-id> --limit 10
   ```

1. **Plan mutations and confirm**: production deployments (`--target prod`), cluster restarts, permission changes, and schema alterations require user authorization; reuse existing authority.

## Gotchas

- **Explicit bundle target**: omitting `--target` uses the bundle's configured default target or fails when none exists; always pass `--target dev` or the intended target explicitly.
- **Token management**: never commit workspace credentials or tokens to version control; use `~/.databrickscfg` or `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment variables.
- **Compute costs**: verify cluster autotermination policies when launching compute to prevent unexpected idle billing.

## Official Skills

- Upstream: Databricks Agent Skills at `databricks/databricks-agent-skills`.

## Documentation

- [Databricks CLI guide](https://docs.databricks.com/en/dev-tools/cli/index.html) · [Databricks Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Unity Catalog guide](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- Releases: [Databricks CLI Releases](https://github.com/databricks/cli/releases)
- Companion skills: [duckdb](../duckdb/SKILL.md) (local data), [python-stack](../python-stack/SKILL.md) (Python development).
