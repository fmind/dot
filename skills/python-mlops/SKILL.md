---
name: python-mlops
description: "Build Python ML pipelines: Polars, Pandera, scikit-learn, MLflow, marimo."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-mlops
  created: "2026-09-16"
  updated: "2026-11-10"
---

# Python MLOps

Build ML workflows from exploration to evaluated delivery, grounded in the [reviewed MLOps repositories](references/sources.md).

## Routing

Read only the matching guide. Go straight to `marimo` for notebooks/reactivity; keep existing project libraries and notebook formats, and treat reference repos as boundary examples rather than mandatory layouts. Confirm permitted compute, tracking stores, and artifact/registry targets before running training, logging, or promotion jobs.

## Task guides

<!-- guides:start -->

- [experiments](references/experiments.md): Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts.
- [marimo](references/marimo.md): Create, debug, convert, and export reactive marimo Python notebooks and apps, including agent pairing.
- [ml-jobs](references/ml-jobs.md): Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture.
- [model-delivery](references/model-delivery.md): Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback.
- [polars](references/polars.md): Transform tabular data with Polars lazy queries and expressions; hand frames to Pandera, scikit-learn, and DuckDB.
- [training](references/training.md): Validate Polars or pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines.

<!-- guides:end -->

## Related owners

- [python-stack](../python-stack/SKILL.md) (uv, typing, packaging, async) · [python-testing](../python-stack/references/python-testing/GUIDE.md) (tests) · [observability](../python-stack/references/observability.md) (telemetry).
- [Colab](../colab/SKILL.md), [Kaggle](../kaggle/SKILL.md), [Hugging Face](../hf/SKILL.md): accounts, sessions, transfers, and compute (available quota never implies authorization).
- [duckdb](../duckdb/SKILL.md) (SQL/file queries) · [python-web](../python-web/SKILL.md) (APIs/demos) · [agent-evaluation](../agent-evaluation/SKILL.md) (agent evals).
