---
name: infra-as-code
description: "Manage OpenTofu/Terraform modules, providers, state/KMS encryption, plans, and tests (tofu, tflint, terraform-docs, tftest)."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/infra-as-code
  created: "2026-09-16"
  updated: "2026-11-27"
---

# Infrastructure as Code

Manage infrastructure with OpenTofu (`tofu`); pin `terraform` in `mise.toml` only when a BSL-only feature or client mandate requires it. Audit modules, IAM, and spend before apply with `fmind-review-terraform`, `fmind-review-security`, and `fmind-review-finops` ([subagent](../subagent/SKILL.md)).

## Defaults

- **Pin tools & hooks**: declare `opentofu`, `tflint`, and `terraform-docs` via `mise use --pin` ([mise.toml](templates/mise.toml), [lefthook.yml](templates/lefthook.yml), [mise](../mise/SKILL.md), [lefthook](../git-delivery/references/lefthook.md)); `mise run build` updates `README.md` via [terraform-docs.yml](templates/terraform-docs.yml).
- **Use keyless auth**: ADC locally and WIF in CI ([cloud-run bootstrap](../gcloud/references/cloud-run/references/bootstrap.md)).

## Workflow

1. **Confirm scope & init**: check root module, backend, `tofu workspace show`, project, and auth; run `mise run install` on fresh clones.
1. **Isolate state**: edit the smallest root module with a unique GCS `prefix` ([in-app layout](references/scaffold.md#opentofu-inside-an-application-repository)).
1. **Gate offline**: run `mise run check` and `mise run test` (`command = plan` + `mock_provider` per [main.tftest.hcl](templates/main.tftest.hcl)).
1. **Plan & CI**: run `mise run plan` (`tmp/plan.tfplan`), never in Git hooks. In CI ([tofu.yml](templates/tofu.yml)), run uncredentialed `validate` on PRs, WIF `plan` on `main`, and `apply` only via `workflow_dispatch` (`apply=true`) behind `environment: production`.
1. **Apply authorized plans**: inspect replacements, destroys, IAM, and cost in `tofu show tmp/plan.tfplan`, run `tofu apply tmp/plan.tfplan`, delete `tmp/plan.tfplan`, and confirm `tofu plan -input=false -detailed-exitcode` exits 0.

## HCL Rules

- **Prefer `for_each` over `count`**: keyed maps avoid cascading destroy/recreate on list shifts.
- **Refactor declaratively**: use `moved`, `import`, and `removed` blocks instead of manual `tofu state` edits.
- **Keep child `modules/` pure**: zero `local-exec`/`remote-exec` provisioners, no `backend`/`provider` blocks inside child `modules/`, and `lifecycle { prevent_destroy = true }` on stateful prod resources (DBs, KMS keys, state buckets).

## State, Secrets & Gotchas

- **Remote state & encryption**: never commit `.tfstate`; use versioned GCS (add KMS encryption per [state-encryption](references/state-encryption.md) when required).
- **Secret hygiene**: gitignore `*.tfvars` (commit `*.example.tfvars`), inject `TF_VAR_<name>` via scoped launchers, and mark secret vars `ephemeral = true` bound to write-only attributes (`secret_data_wo` + `secret_data_wo_version`).
- **CI `tflint` & providers**: pass `GITHUB_TOKEN` to `tflint --init` ([tflint.hcl](templates/tflint.hcl)) and run `tofu init -backend=false` + `tflint --init` before `mise run all` in [ci.yml](../github/references/ci-cd/templates/ci.yml). Review major bumps (`~> 8.0` in [versions.tf](templates/versions.tf)) via [upgrade-tools](../mise/references/upgrade-tools/GUIDE.md).

## Task guides

<!-- guides:start -->

- [scaffold](references/scaffold.md): Scaffold an OpenTofu root module, validate offline, lock providers, and migrate state to GCS.
- [state-encryption](references/state-encryption.md): Configure OpenTofu client-side state and plan encryption with GCP KMS and migrate plaintext state.

<!-- guides:end -->

## Documentation

- [OpenTofu](https://opentofu.org/docs/) · [tflint](https://github.com/terraform-linters/tflint) · [trivy config](https://trivy.dev/docs/latest/scanner/misconfiguration/) · [State encryption](https://opentofu.org/docs/language/state/encryption/) · [releases](https://github.com/opentofu/opentofu/releases)
- Upstream: `hashicorp/agent-skills` ([vendor-skill policy](../agent-harnesses/references/vendor-skills.md)). Companions: [mise](../mise/SKILL.md), [github/ci-cd](../github/references/ci-cd/GUIDE.md), [code-security](../code-security/references/code-review/GUIDE.md), [gcloud](../gcloud/SKILL.md).
