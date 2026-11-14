---
name: google-developer
description: "Find Google developer docs and vendor skills (google/skills) across Cloud, Ads, Analytics, and Identity."
---

# Google Developer Catalog

Discover vendor skills in [google/skills](https://github.com/google/skills); local owners stay authoritative: [gcloud](../SKILL.md), [cloud-run](../../cloud-run/SKILL.md), [infra-as-code](../../infra-as-code/SKILL.md), [gws](../../gws/SKILL.md), [agy](../../agy/SKILL.md), [model-providers](../../model-providers/SKILL.md), [agent-frameworks](../../agent-frameworks/SKILL.md), [colab](../../colab/SKILL.md), and [kaggle](../../kaggle/SKILL.md).

## Workflow

1. **Filter `index.json` by product keyword**:

   ```bash
   curl -fsSL --max-time 10 https://raw.githubusercontent.com/google/skills/main/index.json \
     | jq -r '.skills[] | select((.name + " " + .description) | test("bigquery"; "i")) | .name'
   ```

1. **Audit before installing**: review an immutable snapshot and install project-scoped skills only per [vendor-skill policy](../../agent-project/references/vendor-skills.md) (preview—never install—its colliding `gcloud` guardrail skill per [name collisions](../../agent-project/references/vendor-skills.md#name-collisions)), then cross-check official docs.

| Task                                         | Catalog group and selection                              |
| -------------------------------------------- | -------------------------------------------------------- |
| Compute, data, AI, GKE, operations, security | `cloud`: pair product skill with CLI/auth guardrails.    |
| Advertising APIs and SDKs                    | `ads`: Ads API, Data Manager, Mobile Ads, IMA.           |
| Analytics reporting or configuration         | `analytics`: Data API (reports) vs Admin API (settings). |
| Sign in with Google or token binding         | `identity`: web Sign-In and DPoP.                        |
| Other Google products or docs lookup         | `developers`: `retrieving-developer-knowledge`.          |

## Gotchas

- **Ads spend & credentials**: keep developer tokens and OAuth secrets out of argv/logs; test on sandbox accounts and `validate_only` before authorized live campaign edits.
- **Analytics IDs & quotas**: API numeric property IDs differ from `G-...` measurement IDs; bound queries and keep sensitive exports out of Git.
- **Install individual skills, never full host plugins**: hooks, MCP servers, and permissions stay separate.

## Documentation

- [google/skills](https://github.com/google/skills) · [Google for Developers](https://developers.google.com) · [commits](https://github.com/google/skills/commits/main)
