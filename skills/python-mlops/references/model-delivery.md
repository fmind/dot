---
name: model-delivery
description: "Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback."
---

# Evaluate and Deliver Models

Preparing a model does not authorize changing a production alias or deploying a service; preserve existing authorization for the named destination.

- **Evaluate an explicit version**: resolve `models:/<name>@<alias>` once and record the version; never silently select the newest version. The reference project's promote-before-evaluate and latest-version selection are rejected ([sources](sources.md)).
- **Fail closed on evaluation**: missing or non-finite metrics, unavailable evidence, or a failed threshold stops promotion. Check the installed MLflow API: computing metrics and enforcing thresholds can be separate calls.
- **Promote with a rollback target**: read the current alias and record it, set the alias to the evaluated version, then read it back. A read-then-write is not compare-and-set: reconcile an uncertain or raced write by reading state before retrying. Never delete older versions or artifacts during promotion.
- **Prove delivery at its boundary**: an alias change does not prove serving reloaded the model. For batch, verify written predictions, row identity, and the recorded version; for a service, the running revision's model identity and a representative request.
- **Test the no-alias-on-failure path**: in a disposable registry or injected client, a failing candidate must leave the previous alias intact and call no alias setter.

Service targets: [python-web](../../python-web/SKILL.md), [containerize](../../docker/references/containerize/GUIDE.md), [cloud-run](../../cloud-run/SKILL.md).

## Documentation

- [MLflow model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
