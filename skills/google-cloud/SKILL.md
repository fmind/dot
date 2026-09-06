---
name: google-cloud
description: Map Google Cloud product areas to the official google/skills cloud catalog and install what a task needs. Use for Google Cloud compute, data, AI, GKE, operations, or security work.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/google-cloud
  created: "2026-09-03"
  updated: "2026-09-06"
---

# Google Cloud

Google Cloud is the default cloud for Fmind projects. [gcloud](../gcloud/SKILL.md) owns CLI operations, [cloud-run](../cloud-run/SKILL.md) owns deployment, and [terraform](../terraform/SKILL.md) owns provisioning; this skill maps a product area (compute, data, AI platform, GKE, operations, security, architecture) to the `cloud` group of the official catalog.

## Gotchas

- **Cloud Run first**: GKE skills exist, but install them only in projects that explicitly adopt Kubernetes.
- **Region and project**: `europe-west1` unless the project says otherwise, with account, project, and billing pinned per [gcloud](../gcloud/SKILL.md).
- **Authority**: every installed skill drives `gcloud` under the hood, so mutations, API enablement, and spend still need explicit approval.

## Official Skills

Upstream: `google/skills` (`skills/cloud` group); the CLI guardrail and authentication selections apply broadly, while deeper database and analytics guidance lives in the marketplace's `gemini-cli-extensions/*` sources. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [Google Cloud documentation](https://cloud.google.com/docs) · [google/skills](https://github.com/google/skills)
- Companion skills: [gcloud](../gcloud/SKILL.md), [cloud-run](../cloud-run/SKILL.md), [google-adk](../google-adk/SKILL.md), [terraform](../terraform/SKILL.md), [google-developer](../google-developer/SKILL.md) (any other Google product).
