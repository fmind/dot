---
name: scaffold
description: "Create a new OpenTofu root module from the templates, validate it offline, lock providers, and promote its GCS backend."
---

# Scaffold an OpenTofu Project

Start a new repository from the package templates; the parent [skill](../SKILL.md) owns the stack, state, secrets, and testing standards this guide applies.

## Workflow

1. **Define the project inputs**: `Slug`, GCP `Project ID`, and default `Region`.
1. **Add the config files**:
   - [mise.toml](../templates/mise.toml) and [lefthook.yml](../templates/lefthook.yml); replace the template's `latest` placeholders with exact versions seeded from the workstation lock and commit the generated `mise.lock` per [mise](../../mise/SKILL.md).
   - `.tflint.hcl` from [tflint.hcl](../templates/tflint.hcl) — pins the terraform preset and the GCP ruleset release.
   - `.terraform-docs.yml` from [terraform-docs.yml](../templates/terraform-docs.yml), plus the `TF_DOCS` markers in `README.md`.
   - `dprint.json` per [dprint](../../dprint/SKILL.md), a reviewed project `trivy.yaml` per [trivy](../../code-security/references/trivy/GUIDE.md); `.gitignore` from [gitignore](../templates/gitignore), `.ignore` per [update-ignores](../../repository-maintenance/references/update-ignores/GUIDE.md), `LICENSE` per [project-license](../../project-scaffolding/references/project-license/GUIDE.md).
1. **Write flat root-module sources**: no `modules/` tree until a unit is reused.
   - [versions.tf](../templates/versions.tf) — version constraints, provider pins, and the commented GCS backend and encryption blocks.
   - [main.tf](../templates/main.tf), [variables.tf](../templates/variables.tf) (typed, validated inputs), [outputs.tf](../templates/outputs.tf).
   - [terraform.example.tfvars](../templates/terraform.example.tfvars) — non-secret example and static-scan values; replace the project ID before planning.
   - `tests/main.tftest.hcl` from [main.tftest.hcl](../templates/main.tftest.hcl) — plan-only native tests.
1. **Validate**: `git init --initial-branch=main`, then `mise run install` and `mise run all` — no cloud API access for this starter because the backend is commented and the test uses `mock_provider`; downloading tools/providers still needs network access.
1. **Lock providers**: commit `.terraform.lock.hcl`. Since OpenTofu 1.12, `tofu init` records every platform's checksums from the OpenTofu Registry; run `tofu providers lock -platform=linux_amd64 -platform=darwin_arm64` only for mirror-only installs or providers from other registries.
1. **Promote the backend**: once backend creation and state migration are authorized, create the versioned GCS bucket (commands in [versions.tf](../templates/versions.tf)), back up the current state, verify the source workspace and destination prefix, and uncomment `backend "gcs"`. Run `tofu init -migrate-state` for the reviewed move; authorized non-interactive migration uses `tofu init -migrate-state -force-copy -input=false`. Verify the destination state before removing the local backup.
