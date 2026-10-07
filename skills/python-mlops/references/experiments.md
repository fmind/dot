---
name: experiments
description: "Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts."
---

# Track ML Experiments

Tracking writes to a backend and artifact store: reuse the project's tracker and its current authorization; a local notebook does not authorize uploading data or registering models.

- **Default to a local SQL store**: for a new local MLflow store use `sqlite:///mlflow.db` plus a task-owned artifact directory, both Git-ignored. Migrating an existing tracker is a [data-migration](../../data-migration/SKILL.md) task, never incidental setup.
- **Log deliberately, not everything**: prefer explicit logging; before enabling autologging, disable input-example, dataset, model logging, and registration capture you do not need. Never log raw rows, full resolved configs, environment dumps, or whole output directories; parameters and lineage URIs can leak private data too.
- **Record what makes a run replayable**: code revision and dirty state, environment lock, data digest, split policy, and seeds; a path or seed alone is not reproducibility.
- **Keep effects separate**: logging an artifact, registering a version, and moving an alias are distinct writes; the last two belong to [model-delivery](model-delivery.md).
- **Read back the run**: query its status, metrics, and artifacts; a success message or healthy UI does not prove stored data. Integration tests use a fresh disposable SQLite store, never a copy of a live database.

## Documentation

- [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/) · [releases](https://github.com/mlflow/mlflow/releases).
