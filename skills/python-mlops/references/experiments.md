---
name: experiments
description: "Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts."
---

# Track ML Experiments

Reuse the project's tracker and current authorization; local notebooks do not authorize uploading data or registering models.

- **Default to local SQL**: use `sqlite:///mlflow.db` plus a Git-ignored artifact directory for new local stores. MLflow 3.13+ rejects file stores (`./mlruns`) unless `MLFLOW_ALLOW_FILE_STORE=true` (legacy projects only); run `mlflow migrate-filestore` only as a separate rehearsed migration.
- **Log explicitly, never bulk-dump**: disable unneeded autolog capture (input examples, datasets, models, registration). Never log raw rows, resolved configs, env dumps, whole directories, or PII-bearing lineage URIs/parameters.
- **Record replay state**: commit SHA + dirty flag, lockfile, data digest, split policy, and seeds.
- **Separate write effects**: artifact logging stays here; version registration and alias moves belong to [model-delivery](model-delivery.md).
- **Silence MLflow agent hints**: set `MLFLOW_DISABLE_AGENT_HINT=1`; vendor skill installs follow [vendor-skills](../../agent-project/references/vendor-skills.md).
- **Verify stored runs**: query back run status, metrics, and artifacts; integration tests use a disposable SQLite file, never a live DB copy.

## Documentation

- [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/) · [file store migration](https://mlflow.org/docs/latest/self-hosting/migrate-from-file-store) · [releases](https://github.com/mlflow/mlflow/releases).
