---
name: model-delivery
description: "Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback."
---

# Evaluate and Deliver Models

Preparing a model never authorizes changing a production alias or deploying a service; verify destination authority first.

- **Evaluate an explicit version**: resolve `models:/<name>@<alias>` once and record the version number; never pick `@latest` or promote before evaluating ([sources](sources.md)), and abort promotion on missing metrics or failed thresholds.
- **Promote with rollback**: record the prior alias version, point the alias to the evaluated version, and read it back; never delete older versions or artifacts during promotion.
- **Keep drift alerts gated**: drift alerts and scheduled retraining still pass through explicit evaluation and promotion.

Service targets: [python-web](../../python-web/SKILL.md), [containerize](../../docker/references/containerize/GUIDE.md), [cloud-run](../../cloud-run/SKILL.md).

## Documentation

- [MLflow model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
