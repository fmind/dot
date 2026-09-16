---
name: python-mlops
description: "Build Python ML pipelines: pandas/Pandera, scikit-learn training, MLflow experiments and models, monitoring, and marimo notebooks."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-mlops
  created: "2026-09-16"
  updated: "2026-09-16"
---

# Python MLOps

Develop machine learning workflows from exploration to evaluated delivery, grounded in the [four reviewed MLOps repositories](references/sources.md).

## Routing

Read only the matching guide. For notebook authoring or reactivity, go directly to marimo; experiment tracking and model delivery are separate tasks. Preserve the project's libraries and notebook format. The reference package illustrates boundaries, not a mandatory architecture.

For ML work, establish the prediction target, available data and labels, split policy, success metric, and permitted compute/artifact destinations before running jobs. Training, tracking, registry writes, and promotion have different effects; inspect the selected task's dependencies before execution.

## Task guides

<!-- guides:start -->

- [experiments](references/experiments.md): Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts.
- [marimo](references/marimo.md): Create, debug, convert, and export reactive marimo Python notebooks and apps, including agent pairing.
- [ml-jobs](references/ml-jobs.md): Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture.
- [model-delivery](references/model-delivery.md): Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback.
- [monitoring](references/monitoring.md): Monitor ML data quality, drift, labeled performance, lineage, and bounded model explanations.
- [training](references/training.md): Validate pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines.

<!-- guides:end -->

## Related owners

- [python-stack](../python-stack/SKILL.md): uv, typing, packaging, and async; [python-testing](../python-testing/SKILL.md): test implementation.
- [Colab](../colab/SKILL.md), [Kaggle](../kaggle/SKILL.md), and [Hugging Face](../hf/SKILL.md) retain connector ownership of accounts, sessions, transfers, and compute. Available quota does not authorize allocation.
- [duckdb](../duckdb/SKILL.md): SQL and file queries; [python-web](../python-web/SKILL.md): APIs and model demos; [observability](../observability/SKILL.md): service telemetry; [agent-evaluation](../agent-evaluation/SKILL.md): stochastic agent evaluation.
