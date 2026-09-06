---
name: google-analytics
description: Map Google Analytics API work (Admin API for properties, Data API for reports) to the official google/skills analytics catalog and install what a task needs. Use for any Google Analytics task.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/google-analytics
  created: "2026-09-03"
  updated: "2026-09-05"
---

# Google Analytics

Google Analytics (GA4) exposes two developer APIs: the Admin API manages accounts, properties, data streams, custom dimensions, and key events; the Data API runs reports against a property. Both are Google Cloud APIs enabled on a pinned project per [gcloud](../gcloud/SKILL.md). Dashboards and the web UI are out of scope; this skill routes API work to the `analytics` group of the official catalog.

## Gotchas

- **Identifiers**: API calls take the numeric property (`properties/<id>`), not the `G-...` measurement ID from the tag.
- **Quotas**: limits apply per property and per project; batch report requests and cache results locally (see [duckdb](../duckdb/SKILL.md)) instead of re-querying.
- **Personal data**: reports and exports are personal data by default; keep raw exports out of git and follow the project's retention rule.

## Official Skills

Upstream: `google/skills` (`skills/analytics` group), where Admin selections cover configuration and Data selections cover reporting. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [Analytics Admin API](https://developers.google.com/analytics/devguides/config/admin/v1) · [Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- Companion skills: [gcloud](../gcloud/SKILL.md), [duckdb](../duckdb/SKILL.md), [google-ads](../google-ads/SKILL.md), [google-developer](../google-developer/SKILL.md).
