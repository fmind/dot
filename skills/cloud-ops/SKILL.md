---
name: cloud-ops
description: "Operate cloud/SaaS CLIs: acli (Jira/Confluence), aws, cf (Cloudflare), databricks/genie, hf (Hugging Face), pup (Datadog)."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cloud-ops
  created: "2026-11-21"
  updated: "2026-11-22"
---

# Cloud & Service CLIs

Operate non-GCP cloud, data, observability, and SaaS CLIs safely with explicit account/profile/region pins, bounded JSON reads, secret-safe auth, and approval gates before mutations. `acli`, `databricks`/`genie`, and `hf` install globally in `fmind/dot`; pin `aws`, `cf`, and `pup` per project (`mise use --pin ...`) or host. Use [gcloud](../gcloud/SKILL.md) for GCP, [gws](../gws/SKILL.md) for Google Workspace, and [github](../github/SKILL.md) for GitHub.

## Task guides

<!-- guides:start -->

- [acli](references/acli.md): Search, update Jira and Confluence with acli.
- [aws](references/aws.md): Operate AWS accounts, SSO, IAM, S3, and ECS via aws.
- [cf](references/cf.md): Manage Cloudflare DNS, zones, Workers, Pages, R2, D1, Zero Trust: cf.
- [databricks](references/databricks/GUIDE.md): Operate Databricks bundles, jobs, pipelines, Unity Catalog, genie.
- [hf](references/hf.md): Operate Hugging Face models, datasets, Spaces, jobs: hf.
- [pup](references/pup.md): Query Datadog logs, metrics, traces, monitors, incidents, LLM: pup.

<!-- guides:end -->

## Documentation

- Companions: [gcloud](../gcloud/SKILL.md), [gws](../gws/SKILL.md), [dot-cli](../dot-cli/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md).
