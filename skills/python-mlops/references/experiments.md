---
name: experiments
description: "Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts."
---

# Track ML Experiments

Tracking is a write to the selected backend and artifact destination. Reuse the project's tracker and current authorization; a local notebook does not imply permission to upload its data or register models.

1. **Inspect the installed version and destinations**: read project dependencies, tracking and registry URIs, artifact storage, and task configuration. For a new local MLflow store, prefer an explicit SQL backend such as `sqlite:///mlflow.db` and a task-owned artifact directory. Keep both out of Git. An existing tracker migration is a separate data-migration task; never replace it as incidental setup.
1. **Record run identity**: code revision plus relevant dirty-state evidence, environment lock, resolved non-secret configuration, data version/digest, split policy, random states, and metric definitions. A path or seed alone does not make a run reproducible. Pin immutable input versions when replay matters; record remaining hardware/nondeterminism limits.
1. **Control logging**: prefer explicit logging for small workflows. Before enabling framework autologging, inspect the installed API and disable unnecessary dataset/input-example capture, model logging, or registration. Select only authorized metrics and artifacts. Do not log raw rows, complete resolved configs, environment dumps, or entire output directories by default; parameters and lineage URIs can also reveal private data.
1. **Track meaningful comparisons**: give each trial an identity, preserve parent/child runs when tuning, and label metric direction, split, and baseline. Compare compatible datasets and evaluation protocols. Mark failed or cancelled runs as such and preserve their sanitized cause; do not reuse a successful run ID for unrelated output.
1. **Package an inference contract when requested**: log the complete preprocessing/model artifact, signature, dependency environment, and a synthetic or permitted input example. Validate schema and predict after reload. Logging an artifact, registering a model version, and changing a deployment alias are separate effects; use [model-delivery](model-delivery.md) for the latter steps.
1. **Read back**: query the selected run and verify its status, parameters, metrics, and expected artifact references. Confirm persisted artifacts can be loaded where they will be consumed. A healthy tracking UI or success message does not establish stored data or replay parity.

## Local verification

Use a fresh disposable SQLite store and local artifact directory for tracker integration tests. Where migration setup is expensive, initialize a test template once, close its connections, and copy it per test; never copy a live production database. Keep concurrent tests isolated and verify failed runs as well as successful read-back.

## Documentation

- [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/) · [backend stores](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/) · [model signatures](https://mlflow.org/docs/latest/ml/model/signatures/) · [releases](https://github.com/mlflow/mlflow/releases).
- [observability](../../observability/SKILL.md) owns application logs/traces; [data-migration](../../data-migration/SKILL.md) owns persisted-store changes.
