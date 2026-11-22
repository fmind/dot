---
name: bigquery
description: "Run FinOps-bounded BigQuery dry runs, parameterized SQL, partition pruning, and Polars Storage Read exports."
---

# BigQuery (`bq` & Python Storage Read)

Query and inspect BigQuery datasets safely with hard byte caps, partition pruning, and parameterized SQL ([gcloud](../SKILL.md) owns auth/project identity; [duckdb](../../duckdb/SKILL.md) owns local Parquet/SQLite analysis).

## FinOps Dry-Run & Hard Caps (`bq`)

1. **Always dry-run before querying**: check `totalBytesProcessed` before spending slot/byte quota (`LIMIT` does not reduce bytes scanned without clustering/partitioning or `SELECT *` replacement):
   ```bash
   bq query --project_id=<project-id> --use_legacy_sql=false --dry_run --format=prettyjson \
     'SELECT event_date, count(*) AS n FROM `<project>.<dataset>.<table_id>` WHERE event_date >= @since GROUP BY 1'
   ```
1. **Enforce hard billing caps & parameterized queries**: never interpolate untrusted strings into SQL — pass typed `--parameter`, pin `--maximum_bytes_billed`, and request `--format=prettyjson` or `--format=csv`:
   ```bash
   bq query --project_id=<project-id> --use_legacy_sql=false --nouse_cache \
     --maximum_bytes_billed=1073741824 --format=json \
     --parameter='since:DATE:2026-11-01' \
     'SELECT id, status FROM `<project>.<dataset>.events` WHERE event_date >= @since LIMIT 100'
   ```
1. **Partition & cluster hygiene**: check `bq show --format=prettyjson <project>:<dataset>.<table>` for `timePartitioning` and `clustering` fields before scanning, avoid `SELECT *` on columnar storage, and filter on raw partition columns directly (wrapping columns in `DATE(...)` or functions disables partition pruning unless matching partitioned expression).

## Python, Polars & Gotchas

- **Parameterized client + Storage Read API**: install `'google-cloud-bigquery'` (+ `google-cloud-bigquery-storage` for bulk analytics), configure `QueryJobConfig(maximum_bytes_billed=..., query_parameters=[ScalarQueryParameter(...)])`, pass `job_config.dry_run = True` first for unverified scans, and export large Arrow batches directly into `pl.from_arrow(...)` ([polars](../../mlops/references/polars.md)).
- **Linked datasets (`type = "LINKED"`) inherit `projectReaders`**: `google_logging_linked_dataset` carries `specialGroup: projectReaders` and rejects dataset-level IAM (`HTTP 400`); project `roles/bigquery.dataViewer` or `roles/viewer` grants reads regardless of `roles/logging.viewAccessor`.

## Documentation

- [BigQuery dry runs](https://cloud.google.com/bigquery/docs/dry-run-queries) · [Parameterized queries](https://cloud.google.com/bigquery/docs/parameterized-queries) · [Storage Read API](https://cloud.google.com/bigquery/docs/reference/storage)
