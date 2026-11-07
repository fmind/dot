---
name: model-delivery
description: "Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback."
---

# Evaluate and Deliver Models

Preparing a model does not authorize changing a production alias or deploying a service; preserve existing authorization for the named destination.

- **Evaluate an explicit version**: resolve `models:/<name>@<alias>` once and record the version; never select the newest version, including through the reserved `@latest` alias. The reference project's promote-before-evaluate and latest-version selection are rejected ([sources](sources.md)); missing metrics or a failed threshold stops promotion.
- **Promote with a rollback target**: record the current alias, set it to the evaluated version, then read it back; never delete older versions or artifacts during promotion.
- **Never let drift promote a model**: drift alerts and automated retraining stay within the agreed scope, and every replacement goes through this evaluation and promotion path.

Service targets: [python-web](../../python-web/SKILL.md), [containerize](../../docker/references/containerize/GUIDE.md), [cloud-run](../../cloud-run/SKILL.md).

## Documentation

- [MLflow model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
