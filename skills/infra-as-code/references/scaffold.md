---
name: scaffold
description: "Scaffold an OpenTofu root module, validate offline, lock providers, and migrate state to GCS."
---

# Scaffold an OpenTofu Project

Bootstrap an OpenTofu root module from package templates under the parent [skill](../SKILL.md) rules.

## Workflow

1. **Collect inputs**: `Slug`, GCP `Project ID`, and default `Region`.
1. **Copy configuration files**:
   - [mise.toml](../templates/mise.toml) and [lefthook.yml](../templates/lefthook.yml): pin every `latest` placeholder via `mise use --pin <tool>` (seeding shared tools like `betterleaks`, `dprint`, `lefthook`, and `trivy` from the workstation lock) and commit `mise.lock` ([mise](../../mise/SKILL.md)).
   - `.tflint.hcl` from [tflint.hcl](../templates/tflint.hcl), `.terraform-docs.yml` from [terraform-docs.yml](../templates/terraform-docs.yml) (plus `TF_DOCS` markers in `README.md`), `dprint.json` ([dprint](../../mise/references/dprint.md)), `trivy.yaml` ([trivy](../../code-security/references/trivy/GUIDE.md)), `.gitignore` from [gitignore](../templates/gitignore), `.ignore` ([update-ignores](../../full-review/references/update-ignores/GUIDE.md)), and `LICENSE` ([project-license](../../project-scaffolding/references/project-license/GUIDE.md)).
1. **Create flat root-module files** (defer `modules/` until reuse exists): [versions.tf](../templates/versions.tf), [main.tf](../templates/main.tf), [variables.tf](../templates/variables.tf), [outputs.tf](../templates/outputs.tf), [terraform.example.tfvars](../templates/terraform.example.tfvars) (replace `example-project` before planning), and `tests/main.tftest.hcl` from [main.tftest.hcl](../templates/main.tftest.hcl).
1. **Validate offline**: run `git init --initial-branch=main`, `mise run install`, and `mise run all` (commented backend + `mock_provider` require zero cloud access).
1. **Commit `.terraform.lock.hcl`**: OpenTofu 1.12+ records cross-platform registry hashes on `tofu init`; run `tofu providers lock -platform=linux_amd64 -platform=darwin_arm64` only for mirrors or non-OpenTofu registries.
1. **Promote GCS backend when authorized**: create the versioned bucket per [versions.tf](../templates/versions.tf), back up local state, confirm workspace and GCS `prefix`, uncomment `backend "gcs"`, run `tofu init -migrate-state` (`-force-copy -input=false` when non-interactive migration is approved), and verify remote state before deleting the backup.
