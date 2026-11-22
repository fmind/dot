---
name: model-delivery
description: "Evaluate model versions, MLflow registry aliases, batch scoring, rollback."
---

# Evaluate and Deliver Models

Preparing a model never authorizes changing a production alias or deploying a service; verify destination authority first.

- **Evaluate an explicit version**: resolve `models:/<name>@<alias>` once and record the version number; never pick `@latest` or promote before evaluating ([sources](sources.md)), and abort promotion on missing metrics or failed thresholds.
- **Promote with rollback**: record the prior alias version, point the alias to the evaluated version, and read it back; never delete older versions or artifacts during promotion.
- **Serving parity, drift monitoring, & safe fallback**: bundle preprocessing with model inference so online serving reuses training transforms, enforce input-schema/null-rate and prediction-distribution drift alerts, cap batch sizes and inference timeouts, and define a deterministic safe fallback when model confidence or service health degrades.
- **Keep drift alerts gated**: drift alerts and scheduled retraining still pass through explicit evaluation and promotion.

Service targets: [python](../../python/SKILL.md), [containerize](../../containers/references/containerize/GUIDE.md), [cloud-run](../../gcloud/references/cloud-run/GUIDE.md).

## Documentation

- [MLflow model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
