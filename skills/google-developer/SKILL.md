---
name: google-developer
description: Find official Google skills and developer docs. Use for Cloud, Ads, Analytics, identity, Gemini, Android, Chrome, Web, or Flutter guidance.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/google-developer
  created: "2026-09-03"
  updated: "2026-09-11"
---

# Google Developer Catalog

Route Google product work to the relevant selection in [google/skills](https://github.com/google/skills). Existing owners keep their procedures: [gcloud](../gcloud/SKILL.md) for CLI identity and cloud defaults, [cloud-run](../cloud-run/SKILL.md) for service deployment, [terraform](../terraform/SKILL.md) for provisioning, and [gws](../gws/SKILL.md) for Workspace.

## Workflow

1. Identify the product and operation, then inspect the catalog with `skills add google/skills --list`. Choose the product group below; the developer index can locate guidance in sibling repositories.
1. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) to review the selected immutable snapshot and install only the required project-scoped guidance. A catalog lookup does not authorize executing its results.
1. Compare the selected guidance with installed tools and current official docs before acting. Use [technical-research](../technical-research/SKILL.md) when the API contract is uncertain.

| Task                                           | Catalog group and selection                                                        |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| Compute, data, AI, GKE, operations, security   | `cloud`; select the actual product plus applicable CLI/authentication guidance.    |
| Advertising APIs and SDKs                      | `ads`; distinguish Ads API, Data Manager, Mobile Ads, and IMA.                     |
| Analytics reporting or configuration           | `analytics`; Data API for reports, Admin API for properties and settings.          |
| Another Google product or documentation lookup | `developers` index/docs selection, then the relevant product or identity guidance. |

## Gotchas

- **Ads**: keep developer tokens and OAuth credentials out of arguments and logs. Use test accounts and `validate_only` before authorized live mutations; campaign changes can affect spend.
- **Analytics**: API property IDs differ from `G-...` measurement IDs. Bound queries and exports, account for quotas, and keep sensitive reports out of Git.
- **Installation**: select skills rather than importing an entire host plugin; hooks, MCP servers, and permissions are separate integrations. Cloud defaults and mutation scope remain with the owning workflow.

## Official Skills

Upstream: `google/skills`, with `cloud`, `ads`, `analytics`, `developers`, and `identity` groups. Use its current index for the selected package rather than maintaining a copy of the product catalog.

## Documentation

- [google/skills](https://github.com/google/skills) · [Google for Developers](https://developers.google.com)
- Releases: [google/skills](https://github.com/google/skills/releases)
