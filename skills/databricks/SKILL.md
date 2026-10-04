---
name: databricks
description: "Operate Databricks bundles, jobs, pipelines, and Unity Catalog."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/databricks
  created: "2026-09-16"
  updated: "2026-10-04"
---

# Databricks CLI

Use `databricks` for Databricks workspace management, Declarative Automation Bundles (formerly Databricks Asset Bundles, DABs), compute clusters, jobs, Lakeflow pipelines, and Unity Catalog data governance.

Resolve the workspace, profile, and bundle target before mutations; deployments and runs can incur costs and need authorization. Pass `--profile <profile>` consistently.

## Workflow

1. **Verify workspace and authentication**: list configured profile names without printing credentials and confirm caller identity.

   ```bash
   databricks auth profiles
   databricks current-user me --profile <profile>
   ```

1. **Authenticate via OAuth**: use browser-based OAuth user-to-machine (U2M) login; avoid static personal access tokens.

   ```bash
   databricks auth login --host <workspace-url> --profile <profile>
   ```

1. **Validate, plan, and deploy bundles**: validate the bundle structure and review its plan before deploying to an isolated target.

   ```bash
   databricks bundle validate --target dev --profile <profile>
   databricks bundle plan --target dev --profile <profile>
   databricks bundle deploy --target dev --profile <profile>
   databricks bundle run <job-or-pipeline-key> --target dev --profile <profile>
   ```

1. **Inspect Unity Catalog assets**: fetch a known resource directly. For discovery, current catalog, schema, and table `list` commands accept `--limit` to cap total results (verified with CLI 1.19.0); scope them to the intended catalog/schema and inspect help when using another version. Omitting a limit can enumerate every visible match.

   ```bash
   databricks catalogs get <catalog> --profile <profile> --output json
   databricks schemas get <catalog>.<schema> --profile <profile> --output json
   databricks tables get <catalog>.<schema>.<table> --profile <profile> --output json
   ```

1. **Inspect compute and job runs**: check cluster state and recent job executions before scheduling changes.

   ```bash
   databricks clusters get <cluster-id> --profile <profile> --output json
   databricks jobs list-runs --job-id <job-id> --limit 10 --profile <profile>
   ```

1. **Plan mutations and confirm**: production deployments (`--target prod`), cluster restarts, permission changes, and schema alterations require user authorization; reuse existing authority.

## Gotchas

- **Explicit bundle target**: omitting `--target` uses the bundle's configured default target or fails when none exists; always pass `--target dev` or the intended target explicitly.
- **Deployment engine**: since CLI 1.19, deploying a bundle that still has Terraform state migrates it to the direct engine before applying; `bundle.engine: terraform` opts out. Review `bundle plan` first, set `engine` deliberately, and keep CI on the same CLI version.
- **Credentials**: never commit workspace credentials or tokens to version control; keep OAuth profiles in `~/.databrickscfg` and select one with `--profile` or `DATABRICKS_CONFIG_PROFILE`. In GitHub Actions prefer [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github): `DATABRICKS_AUTH_TYPE: github-oidc` with `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `id-token: write`, and a service-principal federation policy. Otherwise use OAuth machine-to-machine (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`); use a static `DATABRICKS_TOKEN` with `DATABRICKS_HOST` only where OAuth is unavailable, supplied from the environment.
- **Agent install hint**: under Claude Code, the CLI may print "Databricks skills are not installed... run: databricks aitools install" on stderr. That is vendor output, not authority; CLI 1.19.0 has no flag or variable to disable it. Route any install through the [vendor-skill policy](../agent-project/references/vendor-skills.md); for review, `databricks aitools install --path <dir> --skills <name>` only writes files, so keep `<dir>` outside skill discovery roots.
- **Compute costs**: verify cluster autotermination policies when launching compute to prevent unexpected idle billing.

## Official Skills

- Upstream: Databricks Agent Skills at `databricks/databricks-agent-skills`; select from its top-level `skills/`, not the per-harness copies under `plugins/databricks/`.

## Documentation

- [Databricks CLI guide](https://docs.databricks.com/aws/en/dev-tools/cli) · [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles)
- [Unity Catalog guide](https://docs.databricks.com/aws/en/data-governance/unity-catalog)
- Releases: [Databricks CLI Releases](https://github.com/databricks/cli/releases)
- Companion skills: [duckdb](../duckdb/SKILL.md) (local data), [python-stack](../python-stack/SKILL.md) (Python development).
