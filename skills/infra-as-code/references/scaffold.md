---
name: scaffold
description: "Scaffold an OpenTofu root module, validate offline, lock providers, and migrate state to GCS."
---

# Scaffold an OpenTofu Project

Bootstrap an OpenTofu root module from package templates under the parent [skill](../SKILL.md) rules.

## Workflow

1. **Collect inputs**: `Slug`, GCP `Project ID`, and default `Region`.
1. **Copy configuration files**:
   - [mise.toml](../templates/mise.toml) and [lefthook.yml](../templates/lefthook.yml): pin every `latest` placeholder via `mise use --pin <tool>` (seeding shared tools like `betterleaks`, `dprint`, and `trivy` from the workstation lock, and resolving repo-only tools like `git-cliff`, `jactionlint`, `lefthook`, `lychee`, `shellcheck`, and `typos` via `mise use --pin`) and commit `mise.lock` ([mise](../../mise/SKILL.md)).
   - `README.md` from [README.md](../templates/README.md) (keeps `<!-- BEGIN_TF_DOCS -->` / `<!-- END_TF_DOCS -->` markers for `terraform-docs`), `.github/workflows/tofu.yml` from [tofu.yml](../templates/tofu.yml) (GCP WIF keyless plan/apply), `.github/jactionlint.yaml` ([jactionlint.yaml](../../github/templates/jactionlint.yaml)), `.tflint.hcl` from [tflint.hcl](../templates/tflint.hcl), `.terraform-docs.yml` from [terraform-docs.yml](../templates/terraform-docs.yml), [cliff.toml](../../git-delivery/templates/cliff.toml), `CHANGELOG.md` stub, [dprint.json](../../mise/templates/dprint.json), [trivy.yaml](../../code-security/references/trivy/templates/trivy.yaml), [betterleaks.toml](../../code-security/templates/betterleaks.toml) (`.betterleaks.toml`), `.gitignore` from [gitignore](../templates/gitignore), `.ignore` ([update-ignores](../../full-review/references/update-ignores/GUIDE.md)), and `LICENSE` ([project-license](../../github/references/project-license/GUIDE.md)).
1. **Create flat GCP root-module files** (defer `modules/` until reuse exists): [versions.tf](../templates/versions.tf), [main.tf](../templates/main.tf), [variables.tf](../templates/variables.tf), [outputs.tf](../templates/outputs.tf), [terraform.example.tfvars](../templates/terraform.example.tfvars) (replace `example-project` before planning), and `tests/main.tftest.hcl` from [main.tftest.hcl](../templates/main.tftest.hcl).
1. **Validate offline**: run `git init --initial-branch=main`, `mise run install`, and `mise run all` (commented backend + `mock_provider` require zero cloud access).
1. **Commit `.terraform.lock.hcl`**: OpenTofu 1.12+ records cross-platform registry hashes on `tofu init`; run `tofu providers lock -platform=linux_amd64 -platform=darwin_arm64` only for mirrors or non-OpenTofu registries.
1. **Promote GCS backend when authorized**: create the versioned bucket per [versions.tf](../templates/versions.tf), back up local state, confirm workspace and GCS `prefix`, uncomment `backend "gcs"`, run `tofu init -migrate-state` (`-force-copy -input=false` when non-interactive migration is approved), and verify remote state before deleting the backup.

## OpenTofu inside an application repository

- **Keep modules in `infra/`**: extend the app's `mise.toml` (`check:tofu` running `tofu -chdir=infra ...`, `tflint --chdir=infra`, and `trivy --config trivy.yaml fs --tf-vars infra/terraform.example.tfvars .`), `install` (`tofu -chdir=infra init` + `tflint --chdir=infra --init`), `test` (`tofu -chdir=infra test`), `lefthook.yml` (`**/*.{tf,tofu,tfvars,tftest.hcl,tofutest.hcl}`), and `.gitignore`/`.dockerignore` (`*.tfstate*`, `*.tfplan`, `**/.terraform`).
- **Isolate offline validation**: pass `env.TF_DATA_DIR = "../tmp/tofu-check"` (resolved from `infra/`) to `tofu -chdir=infra init -backend=false -input=false -lockfile=readonly` (and in CI pass `GITHUB_TOKEN` to `tflint --chdir=infra --init` before `mise run all`).
