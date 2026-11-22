---
name: remote-storage
description: "Remote object storage (S3, GCS, HTTP, Hugging Face) and extensions: install, load, and credential providers."
---

# Remote Storage and Extensions

Read this before querying remote object storage or loading a DuckDB extension; local CSV, Parquet, and JSON work needs neither.

- **Extensions load on demand**: `httpfs`, `spatial`, `postgres` install once with `INSTALL <ext>; LOAD <ext>;` and need network the first time.
- **Use the selected extension's credential provider**: never literal credentials in SQL. Core `httpfs` accesses GCS through the S3 API and needs HMAC credentials; its `credential_chain` does not consume Google ADC. ADC requires a separately reviewed compatible extension, such as the community [gcs extension](https://duckdb.org/community_extensions/extensions/gcs), or downloading through an authorized Google client first.
- **Configure S3 options through secrets**: DuckDB 2.0 disables S3 URL parameters, so `?s3_region=...` becomes part of the object key; set region, endpoint, and credentials with `CREATE SECRET`.
- **Query Hub datasets in place**: `httpfs` reads `hf://datasets/<owner>/<name>@<revision>/<path>`; pin the revision, and use `CREATE SECRET (TYPE huggingface, PROVIDER credential_chain)` for gated or private data.
