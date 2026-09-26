---
name: infra-as-code
description: "Manage OpenTofu/Terraform infrastructure, providers, state, plans, and migrations."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/infra-as-code
  created: "2026-09-16"
  updated: "2026-09-26"
---

# Infrastructure as Code

Canonical infrastructure as code with OpenTofu (the open-source Terraform fork; the binary is `tofu`). A repository that needs a BSL-licensed feature or employer-mandated HashiCorp Terraform pins `terraform` in its own mise configuration and documents the deviation.

## 1. Core Stack

- **Engine**: OpenTofu via mise (`opentofu` tool, `tofu` binary); verify provider, backend, state, and language-feature compatibility before migration; OpenTofu also supports client-side state encryption.
- **Tasks and hooks**: [mise.toml](templates/mise.toml) exposes the canonical vocabulary per [mise](../mise/SKILL.md) — `check` fans out to format, validate, lint (tflint), scan (trivy), and leaks; [lefthook.yml](templates/lefthook.yml) wires the hooks per [lefthook](../github-actions/references/lefthook.md).
- **Docs**: `terraform-docs` injects the inputs/outputs table into `README.md` between `<!-- BEGIN_TF_DOCS -->` / `<!-- END_TF_DOCS -->` markers, configured by [terraform-docs.yml](templates/terraform-docs.yml).
- **Cloud planning is explicit**: `build` generates documentation; `mise run plan` creates `tmp/plan.tfplan` only for the selected backend, workspace, and cloud target. A plan can access APIs, state, and data sources. Applying it requires the authorized target and reviewed plan (`tofu apply tmp/plan.tfplan`); keep plan and apply out of automatic gates.

## 2. Project Scaffolding Workflow

1. **Information**: define the project `Slug`, GCP `Project ID`, and default `Region`.
1. **Config files**:
   - [mise.toml](templates/mise.toml) and [lefthook.yml](templates/lefthook.yml); replace the template's `latest` placeholders with exact versions from the workstation baseline and commit the generated `mise.lock` per [mise](../mise/SKILL.md).
   - `.tflint.hcl` from [tflint.hcl](templates/tflint.hcl) — pins the terraform preset and the GCP ruleset release.
   - `.terraform-docs.yml` from [terraform-docs.yml](templates/terraform-docs.yml), plus the `TF_DOCS` markers in `README.md`.
   - `dprint.json` per [dprint](../dprint/SKILL.md), a reviewed project `trivy.yaml` per [trivy](../security-review/references/trivy/GUIDE.md); `.gitignore` from [gitignore](templates/gitignore), `LICENSE` per [project-license](../project-scaffolding/references/project-license/GUIDE.md).
1. **Sources** (flat root module; no `modules/` tree until a unit is reused):
   - [versions.tf](templates/versions.tf) — version constraints, provider pins, and the commented GCS backend and encryption blocks.
   - [main.tf](templates/main.tf), [variables.tf](templates/variables.tf) (typed, validated inputs), [outputs.tf](templates/outputs.tf).
   - [terraform.example.tfvars](templates/terraform.example.tfvars) — non-secret example and static-scan values; replace the project ID before planning.
   - `tests/main.tftest.hcl` from [main.tftest.hcl](templates/main.tftest.hcl) — plan-only native tests.
1. **Validate**: `git init --initial-branch=main`, then `mise run install` and `mise run all` — no cloud API access for this starter because the backend is commented and the test uses `mock_provider`; downloading tools/providers still needs network access.
1. **Lock providers**: commit `.terraform.lock.hcl`; on multi-platform teams run `tofu providers lock -platform=linux_amd64 -platform=darwin_arm64`.
1. **Promote the backend**: once backend creation and state migration are authorized, create the versioned GCS bucket (commands in [versions.tf](templates/versions.tf)), back up the current state, verify the source workspace and destination prefix, and uncomment `backend "gcs"`. Run `tofu init -migrate-state` for the reviewed move; authorized non-interactive migration uses `tofu init -migrate-state -force-copy -input=false`. Verify the destination state before removing the local backup.

## 3. State & Secrets

- **State is secret**: state can store sensitive resource attributes in plaintext — never in git, always in the versioned GCS bucket, ideally wrapped by OpenTofu's `encryption` block (GCP KMS, sketched in [versions.tf](templates/versions.tf)).
- **Variable files**: `*.tfvars` is gitignored; commit only `*.example.tfvars`. Feed secrets at plan time per [sops-secrets](../sops-secrets/SKILL.md): `sops exec-env secrets.enc.env 'tofu plan -out=tmp/plan.tfplan'` with `TF_VAR_<name>` entries.
- **Credentials**: Application Default Credentials locally; Workload Identity Federation in CI per [github-actions](../github-actions/references/ci-cd/GUIDE.md) — no service-account keys.

## 4. Testing Standard

- **Native tests first**: `tofu test` over `tests/*.tftest.hcl` with `command = plan` asserts on planned attributes ([main.tftest.hcl](templates/main.tftest.hcl)) ; the supplied `mock_provider` keeps this starter offline. Plan mode alone can still authenticate, refresh state, and read data sources.
- **Apply-mode tests**: `command = apply` creates real (then destroyed) resources; reserve it for behavior a plan cannot prove, with approved project access and cost.
- **Policy checks**: encode "must never happen" rules (public buckets, missing labels) as `check:scan` trivy findings or plan-test assertions.

## Gotchas

- **`tofu init` before everything**: `check:validate`, `check:lint`, and `test` need providers downloaded; a fresh clone runs `mise run install` first.
- **tflint rulesets are downloaded**: `tflint --init` (in `install:lint`) fetches the plugins pinned in [tflint.hcl](templates/tflint.hcl); export `GITHUB_TOKEN` in CI to avoid API rate limits.
- **terraform-docs needs markers**: `inject` mode only rewrites between the `TF_DOCS` markers; add them to `README.md` once at scaffold time.
- **Provider majors move fast**: [versions.tf](templates/versions.tf) pins the google provider to one major with `~>`; bump majors deliberately with [upgrade-tools](../upgrade-tools/SKILL.md) and read the upgrade guide, because resources rename across majors.
- **One state per concern**: several small root modules (one per GCS `prefix`) beat one monolithic state — smaller blast radius, faster plans.

## Official Skills

Upstream: `hashicorp/agent-skills`; follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select only the Terraform or provider guidance needed by the stack.

## Documentation

- [OpenTofu](https://opentofu.org/docs/) · [tflint](https://github.com/terraform-linters/tflint) · [trivy config](https://trivy.dev/latest/docs/scanner/misconfiguration/) · [terraform-docs](https://terraform-docs.io) · [State encryption](https://opentofu.org/docs/language/state/encryption/)
- Releases: [OpenTofu](https://github.com/opentofu/opentofu/releases) · [what's new](https://opentofu.org/docs/intro/whats-new/)
- Companion skills: [mise](../mise/SKILL.md) (task vocabulary), [sops-secrets](../sops-secrets/SKILL.md) (encrypted variables), [github-actions](../github-actions/references/ci-cd/GUIDE.md) (CI), [security-review](../security-review/references/code-review/GUIDE.md) (full-repo scans), [Google catalog](../google-developer/SKILL.md) (product skills).
