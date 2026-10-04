---
name: infra-as-code
description: "Manage OpenTofu/Terraform modules, providers, state, and plans."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/infra-as-code
  created: "2026-09-16"
  updated: "2026-10-04"
---

# Infrastructure as Code

Canonical infrastructure as code with OpenTofu (the open-source Terraform fork; the binary is `tofu`). A repository that needs a BSL-licensed feature or employer-mandated HashiCorp Terraform pins `terraform` in its own mise configuration and documents the deviation.

## Defaults

- **Engine**: OpenTofu via mise (`opentofu` tool, `tofu` binary); verify provider, backend, state, and language-feature compatibility before a Terraform migration.
- **Tasks and hooks**: [mise.toml](templates/mise.toml) exposes the canonical vocabulary per [mise](../mise/SKILL.md) — `check` fans out to format, validate, lint (tflint), scan (trivy), and leaks; [lefthook.yml](templates/lefthook.yml) wires the hooks per [lefthook](../github-actions/references/lefthook.md).
- **Docs**: `terraform-docs` injects the inputs/outputs table into `README.md` between `<!-- BEGIN_TF_DOCS -->` / `<!-- END_TF_DOCS -->` markers, configured by [terraform-docs.yml](templates/terraform-docs.yml); `mise run build` regenerates it without cloud access.
- **Credentials**: Application Default Credentials locally; Workload Identity Federation in CI per [github-actions](../github-actions/references/ci-cd/GUIDE.md) — no service-account keys.
- **New repositories** follow the [scaffold](references/scaffold.md) guide.

## Workflow

1. **Resolve the target**: identify the root module, backend, workspace (`tofu workspace show`), cloud project, credentials, and the authorized change scope. A fresh clone runs `mise run install` first: validation, linting, and tests need `tofu init` providers and `tflint --init` rulesets.
1. **Edit minimally**: change the smallest root module that owns the resource; keep one state per concern.
1. **Check before planning**: run `mise run check` and `mise run test`; tests stay offline only while every provider is mocked (the starter's `mock_provider`), otherwise plan-mode tests can authenticate, refresh state, and read data sources. Native tests over `tests/*.tftest.hcl` use `command = plan` ([main.tftest.hcl](templates/main.tftest.hcl)); encode "must never happen" rules (public buckets, missing labels) as `check:scan` trivy findings or plan-test assertions.
1. **Plan explicitly**: `mise run plan` writes `tmp/plan.tfplan` for the selected backend, workspace, and cloud target; feed secrets per State and secrets below. A plan can access APIs, state, and data sources, so keep plan and apply out of automatic gates.
1. **Review the plan**: read `tofu show tmp/plan.tfplan` and flag every replacement, destroy, IAM change, and cost-relevant resource before asking for apply authority.
1. **Apply the reviewed plan when authorized**: `tofu apply tmp/plan.tfplan` against the same target, then delete the saved plan.
1. **Verify**: re-read the changed resources and run the same target's plan with its secret inputs, e.g. `sops exec-env secrets.enc.env 'tofu plan -input=false -detailed-exitcode'`; exit 0 means no remaining drift, 2 means pending changes, 1 is an error.

## State and secrets

- **State is secret**: state can store sensitive resource attributes in plaintext — never in git, always in the versioned GCS bucket, ideally wrapped by OpenTofu's `encryption` block. Read [state-encryption](references/state-encryption.md) before enabling it or migrating existing state.
- **Variable files**: `*.tfvars` is gitignored; commit only `*.example.tfvars`. Feed secrets per [sops-secrets](../sops-secrets/SKILL.md) as `TF_VAR_<name>` entries: `sops exec-env secrets.enc.env 'tofu plan -out=tmp/plan.tfplan'`. A saved plan stores ordinary variable values, sensitive ones included; declare secret inputs `ephemeral = true`, pass them only to write-only arguments (for example `secret_data_wo` with an incremented `secret_data_wo_version`), and supply them again at apply: `sops exec-env secrets.enc.env 'tofu apply tmp/plan.tfplan'`.

## Gotchas

- **Apply-mode tests create resources**: `command = apply` creates real (then destroyed) resources; reserve it for behavior a plan cannot prove, with approved project access and cost.
- **tflint rulesets are downloaded**: `tflint --init` (in `install:lint`) fetches the plugins pinned in [tflint.hcl](templates/tflint.hcl); export `GITHUB_TOKEN` in CI to avoid API rate limits.
- **terraform-docs needs markers**: `inject` mode only rewrites between the `TF_DOCS` markers; add them to `README.md` once at scaffold time.
- **Provider majors move fast**: [versions.tf](templates/versions.tf) pins the google provider to one major with `~>`; bump majors deliberately with [upgrade-tools](../upgrade-tools/SKILL.md) and read the upgrade guide, because resources rename across majors.
- **One state per concern**: several small root modules (one per GCS `prefix`) beat one monolithic state — smaller blast radius, faster plans.

## Task guides

<!-- guides:start -->

- [scaffold](references/scaffold.md): Create a new OpenTofu root module from the templates, validate it offline, lock providers, and promote its GCS backend.
- [state-encryption](references/state-encryption.md): Enable OpenTofu client-side state and plan encryption with GCP KMS, including plaintext state migration.

<!-- guides:end -->

## Documentation

- [OpenTofu](https://opentofu.org/docs/) · [tflint](https://github.com/terraform-linters/tflint) · [trivy config](https://trivy.dev/docs/latest/scanner/misconfiguration/) · [terraform-docs](https://terraform-docs.io) · [State encryption](https://opentofu.org/docs/language/state/encryption/)
- Releases: [OpenTofu](https://github.com/opentofu/opentofu/releases) · [what's new](https://opentofu.org/docs/intro/whats-new/)
- Upstream: `hashicorp/agent-skills` per the [vendor-skill policy](../agent-project/references/vendor-skills.md); select only the Terraform or provider guidance the stack needs.
- Companion skills: [mise](../mise/SKILL.md) (task vocabulary), [sops-secrets](../sops-secrets/SKILL.md) (encrypted variables), [github-actions](../github-actions/references/ci-cd/GUIDE.md) (CI), [code-security](../code-security/references/code-review/GUIDE.md) (full-repo scans), [Google catalog](../google-developer/SKILL.md) (product skills).
