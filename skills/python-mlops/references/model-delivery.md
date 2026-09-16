---
name: model-delivery
description: "Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback."
---

# Evaluate and Deliver Models

Use this guide for registry versions and inference contracts. Preserve existing authorization for the named destination; preparing a model does not by itself authorize changing a production alias or deploying a service.

1. **Resolve identity**: select an explicit registered model and version, its source run/artifact, input schema, and evaluation data revision. MLflow `models:/<name>/<version>` identifies a version; `models:/<name>@<alias>` follows a mutable alias. Resolve an alias once and record the version for evaluation and reproducible batches. Do not silently select the newest version.
1. **Evaluate that candidate**: use the agreed held-out data, metric direction, absolute thresholds, baseline comparison, and relevant slices. Verify feature/target alignment and exercise the reloaded artifact. Check the installed evaluation API: calculating metrics and enforcing thresholds may be separate calls. Missing metrics, non-finite results, unavailable evaluation evidence, or failed thresholds stop promotion.
1. **Prepare promotion**: bind the passing evaluation to the exact candidate version, data revision, and policy. Read the current alias and retain the prior version for rollback. If another writer changes the alias before the update, re-evaluate the intended operation; serialize promotion through the project's supported mechanism where races matter. A read followed by a write is not an atomic compare-and-set.
1. **Apply within scope**: only after the required evaluation passes, set the intended alias to the evaluated version and read it back. An uncertain write must be reconciled by reading current state before retrying. Do not delete older versions or artifacts as part of promotion. Record the resulting version and rollback target; changing an alias alone does not prove serving processes loaded the model.
1. **Verify inference**: load the complete model with its preprocessing and declared environment. Validate input schema, missing/extra columns, unseen categories, empty batches, and feature order. Preserve row identity/cardinality in prediction outputs; never silently align frames by an unrelated index. Bound batch size and use safe output replacement or resumable partitions where needed. Read back the written predictions and compare against the local loaded artifact within the stated tolerance.
1. **Prove delivery at its actual boundary**: for a batch, verify output data plus recorded model version; for a service, verify the running revision's model identity and a representative request. Use [python-web](../../python-web/SKILL.md), [containerize](../../containerize/SKILL.md), and [cloud-run](../../cloud-run/SKILL.md) only when those delivery targets are in scope.

## Failure check

In a disposable registry or injected client, make a candidate fail evaluation and assert no alias setter is called and the previous alias remains intact. Then exercise a passing explicit version, read-back mismatch, and rollback to the recorded prior version. These checks qualify the promotion boundary; repeat the relevant integration check before claiming a real registry or serving deployment works.

## Documentation

- [MLflow model registry](https://mlflow.org/docs/latest/ml/model-registry/) · [evaluation](https://mlflow.org/docs/latest/ml/evaluation/) · [releases](https://github.com/mlflow/mlflow/releases).
