---
name: infra-as-code
description: "Manage OpenTofu/Terraform modules, providers, state, and plans."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/infra-as-code
  created: "2026-09-16"
  updated: "2026-11-11"
---

# Infrastructure as Code

Manage infrastructure with OpenTofu (`tofu`); pin HashiCorp `terraform` in `mise.toml` only when a BSL-only feature or client mandate requires it, documenting why.

## Defaults

- **Pin project tools in `mise.toml`**: declare `opentofu`, `tflint`, and `terraform-docs` via `mise use --pin <tool>` ([mise.toml](templates/mise.toml); workstation `tofu`/`tflint` exist only for editor support, and verify provider/backend/state compatibility before migrating from Terraform).
- **Align tasks, hooks, and docs**: [mise.toml](templates/mise.toml) and [lefthook.yml](templates/lefthook.yml) wire format, validate, `tflint`, `trivy`, and `betterleaks` ([mise](../mise/SKILL.md), [lefthook](../github-actions/references/lefthook.md)); `mise run build` injects `TF_DOCS` tables into `README.md` offline via [terraform-docs.yml](templates/terraform-docs.yml).
- **Use keyless auth**: ADC locally and Workload Identity Federation in CI ([cloud-run bootstrap](../cloud-run/references/bootstrap.md)).

## Workflow

1. **Confirm target and initialize**: verify root module, backend, `tofu workspace show`, cloud project, credentials, and change scope; run `mise run install` on fresh clones (`tofu init` + `tflint --init`).
1. **Isolate state per concern**: edit the smallest owning root module, using a distinct GCS `prefix` per module.
1. **Gate offline first**: run `mise run check` and `mise run test` (`tests/*.tftest.hcl` use `command = plan` with `mock_provider` as in [main.tftest.hcl](templates/main.tftest.hcl); unmocked plan tests hit cloud APIs/state). Encode invariants as `check:scan` Trivy checks or plan assertions.
1. **Plan on demand**: run `mise run plan` (`tmp/plan.tfplan`), keeping `plan` and `apply` out of hooks/CI gates.
1. **Apply reviewed plans only when authorized**: highlight replacements, destroys, IAM, and cost in `tofu show tmp/plan.tfplan`, run `tofu apply tmp/plan.tfplan`, delete `tmp/plan.tfplan`, and verify `tofu plan -input=false -detailed-exitcode` exits 0.

## OpenTofu inside an application repository

- **Keep modules in `infra/`**: expose one `check:tofu` task calling `tofu -chdir=infra ...` and `tflint --chdir=infra` rather than duplicating standalone tasks.
- **Isolate offline validation**: pass `env.TF_DATA_DIR = "../tmp/tofu-check"` (resolved from `infra/`) to `tofu -chdir=infra init -backend=false -input=false -lockfile=readonly` so cached live backends never touch remote state.

## State and secrets

- **Encrypt versioned remote state**: never commit `.tfstate`; store state in versioned GCS with OpenTofu client-side KMS encryption ([state-encryption](references/state-encryption.md)).
- **Keep secrets out of tfvars and `.tfplan`**: gitignore `*.tfvars` (commit only `*.example.tfvars`), inject `TF_VAR_<name>` via scoped secret launchers into `tofu` only, and declare secret variables `ephemeral = true` bound solely to write-only attributes (e.g. `secret_data_wo` + `secret_data_wo_version`), re-supplying them at `tofu apply tmp/plan.tfplan`.

## Gotchas

- **`command = apply` creates real cloud resources**: use only with explicit project and spend approval.
- **Pass `GITHUB_TOKEN` in CI for `tflint --init`** ([tflint.hcl](templates/tflint.hcl)) and run `tofu init -backend=false` + `tflint --init` before `mise run all` in [ci.yml](../github-actions/references/ci-cd/templates/ci.yml).
- **Review provider major upgrades**: [versions.tf](templates/versions.tf) constrains Google to `~> 8.0`; read provider upgrade guides when bumping majors via [upgrade-tools](../upgrade-tools/SKILL.md).

## Task guides

<!-- guides:start -->

- [scaffold](references/scaffold.md): Scaffold an OpenTofu root module, validate offline, lock providers, and migrate state to GCS.
- [state-encryption](references/state-encryption.md): Configure OpenTofu client-side state and plan encryption with GCP KMS and migrate plaintext state.

<!-- guides:end -->

## Documentation

- [OpenTofu](https://opentofu.org/docs/) · [tflint](https://github.com/terraform-linters/tflint) · [trivy config](https://trivy.dev/docs/latest/scanner/misconfiguration/) · [terraform-docs](https://terraform-docs.io) · [State encryption](https://opentofu.org/docs/language/state/encryption/) · [releases](https://github.com/opentofu/opentofu/releases)
- Upstream: `hashicorp/agent-skills` via [vendor-skill policy](../agent-project/references/vendor-skills.md).
- Companion skills: [mise](../mise/SKILL.md), [github-actions](../github-actions/references/ci-cd/GUIDE.md), [code-security](../code-security/references/code-review/GUIDE.md), [gcloud](../gcloud/references/google-developer.md).
