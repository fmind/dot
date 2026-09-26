---
name: gcloud
description: "Use gcloud for Google Cloud projects, IAM, billing, APIs, logs, and diagnostics."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gcloud
  created: "2026-08-30"
  updated: "2026-09-26"
---

# Google Cloud CLI

Use `gcloud` for bounded account, project, IAM, API, billing, logging, and audit operations. [cloud-run](../cloud-run/SKILL.md) owns deployment, [infra-as-code](../infra-as-code/SKILL.md) owns provisioned infrastructure, and [incident-response](../incident-response/SKILL.md) owns a live outage.

## Defaults

Google Cloud is the default cloud for Fmind projects, with `europe-west1` unless the project says otherwise. Prefer Cloud Run for services; use GKE only when the project explicitly adopts Kubernetes. Existing project choices take precedence.

## Workflow

1. **Resolve identity and scope**: inspect the named configuration, account, project, and billing project; never activate another configuration just to make a command work.

   ```bash
   gcloud config configurations list --format='table(name,is_active)'
   gcloud config configurations describe <configuration> --format=json
   gcloud config get auth/impersonate_service_account --configuration <configuration>
   gcloud config get auth/access_token_file --configuration <configuration>
   gcloud projects describe <project-id> --format='json(projectId,projectNumber,lifecycleState)'
   ```

1. **Pin every consequential call**: pass `--configuration`, `--account`, `--project`, and `--billing-project` (plus `--impersonate-service-account` for an approved chain) so terminal defaults cannot redirect the operation.
1. **Start read-only**: inspect the resources needed for the question, bounded by project, resource, and time window. Use supported `--filter` and `--limit` on listings and selected fields in `--format`; for logs, constrain time and resource before projecting message fields. Keep full IAM policies or configuration when required for the review; a limited listing is not an exhaustive audit. `--quiet` controls prompts, not output volume.
1. **Plan the mutation**: state the resource, before and after state, permissions, cost or quota impact, rollback, and verification command; API enablement, IAM, billing, deletion, and production changes need explicit authority.
1. **Apply minimally and verify**: change only the named resource, then re-read it and its operation or audit status; separate local configuration, accepted request, completed operation, and user-visible outcome.

## Gotchas

- **`--quiet` is not authority**: it suppresses prompts; it neither makes an operation safe nor approves it.
- **Overrides replace the account**: `CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT`, `CLOUDSDK_AUTH_ACCESS_TOKEN_FILE`, and `--impersonate-service-account` change the effective principal; prove which is active first.
- **Failures are findings**: on an auth, permission, or quota error report the missing principal, denied permission, or exhausted quota; do not switch configurations, broaden IAM, create keys, or move spend to another project.

## Official Skills

Upstream: `google/skills` (`skills/cloud`), listed and installed through [Google catalog](../google-developer/SKILL.md); its CLI guardrail skill applies to every `gcloud` call.

## Documentation

- [gcloud reference](https://cloud.google.com/sdk/gcloud/reference) · [Authorize the gcloud CLI](https://cloud.google.com/sdk/docs/authorizing)
- Releases: [gcloud release notes](https://cloud.google.com/sdk/docs/release-notes)
- Companion skills: [Google catalog](../google-developer/SKILL.md) (which upstream skill), [cloud-run](../cloud-run/SKILL.md) (deploy), [infra-as-code](../infra-as-code/SKILL.md) (provision), [incident-response](../incident-response/SKILL.md) (outage).
