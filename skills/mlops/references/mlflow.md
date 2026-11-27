---
name: mlflow
description: "Track MLflow experiments, lineage, and GenAI evals; evaluate, alias-promote, and roll back models."
---

# MLflow Tracking, Registry & Model Delivery

Reuse the project's tracker and registry authority; local notebooks never authorize uploading data, registering models, changing production aliases, or deploying services.

## Tracking

- **Default to local SQL (`mlflow>=3.18.0`)**: use `sqlite:///mlflow.db` plus a Git-ignored artifact directory for new local stores. MLflow 3.13+ rejects file stores (`./mlruns`) unless `MLFLOW_ALLOW_FILE_STORE=true` (legacy projects only); run `mlflow migrate-filestore` only as a separate rehearsed migration.
- **Log explicitly, never bulk-dump**: disable unneeded autolog capture (input examples, datasets, models, registration). Never log raw rows, resolved configs, env dumps, whole directories, or PII-bearing lineage URIs/parameters.
- **Record replay state & verify runs**: log commit SHA + dirty flag, lockfile, data digest, split policy, and seeds; query back stored run status, metrics, and artifacts (integration tests use a disposable SQLite file, never a live DB copy).
- **Silence MLflow agent hints**: set `MLFLOW_DISABLE_AGENT_HINT=1`; vendor skill installs follow [vendor-skills](../../agent-harnesses/references/vendor-skills.md).
- **GenAI tracing & evals (`mlflow.genai`)**: use `@mlflow.trace`, `@mlflow.genai.scorer`, `mlflow.genai.evaluate(...)`, and `mlflow.genai.compare_evaluations(...)` for agent/LLM runs ([evaluation](../../agent-frameworks/references/evaluation/GUIDE.md)), redacting raw secrets and PII.

## Registry & Promotion

- **Separate write effects & evaluate an explicit version**: keep artifact logging separate from registration and alias moves. Resolve `models:/<name>@<alias>` once and record the exact version number; never pick `@latest` or promote before evaluating ([sources](sources.md)), and abort promotion on missing metrics or failed champion-vs-challenger thresholds.
- **Promote with rollback**: record the prior alias version, point the alias to the evaluated version, and read it back; never delete older versions or artifacts during promotion.
- **Serving parity, drift monitoring, & safe fallback**: bundle preprocessing with model inference so online serving reuses training transforms, enforce input-schema/null-rate and prediction-distribution drift alerts, cap batch sizes and inference timeouts, and define a deterministic safe fallback when model confidence or service health degrades. Drift alerts and scheduled retraining still pass through explicit evaluation and promotion.

Service targets: [python](../../python/SKILL.md), [containerize](../../containers/references/containerize/GUIDE.md), [cloud-run](../../gcloud/references/cloud-run/GUIDE.md).

## Documentation

- [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/) · [file store migration](https://mlflow.org/docs/latest/self-hosting/migrate-from-file-store) · [model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
