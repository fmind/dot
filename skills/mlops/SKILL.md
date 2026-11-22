---
name: mlops
description: "Build Python ML/MLOps pipelines and notebooks: Polars, Pandera, scikit-learn, LightGBM, Optuna, PyTorch, vLLM, MLflow, marimo, Airflow, Kaggle."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mlops
  created: "2026-11-22"
  updated: "2026-11-22"
---

# Python MLOps

Build ML workflows from exploration to evaluated delivery, grounded in [reviewed MLOps repos](references/sources.md). Load the matching guide(s) (`marimo` for notebooks, keeping existing libraries/formats), confirm compute/registry targets before running jobs or promotions, and audit pipelines with `fmind-review-mlops` and `fmind-review-data` (plus `fmind-review-visuals` on plots; [subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [experiments](references/experiments.md): MLflow experiment tracking, lineage, metrics, signatures, and artifacts.
- [gpu-and-serving](references/gpu-and-serving.md): PyTorch CUDA/CPU uv indexes, safetensors, and bounded vLLM GPU serving.
- [marimo](references/marimo.md): Reactive marimo Python notebooks and apps, export, and agent pairing.
- [ml-jobs](references/ml-jobs.md): Package notebooks into typed ML jobs and MLOps reference architectures.
- [model-delivery](references/model-delivery.md): Evaluate model versions, MLflow registry aliases, batch scoring, rollback.
- [orchestration-and-competitions](references/orchestration-and-competitions.md): Airflow DAGs with astro and Kaggle downloads, kernels, and submissions.
- [polars](references/polars.md): Polars lazy tabular pipelines; hand off to Pandera, scikit-learn, DuckDB.
- [training](references/training.md): Pandera schema validation, leakage checks, and scikit-learn pipelines.

<!-- guides:end -->

## Documentation

- [Source map](references/sources.md) (each guide links its upstream docs).
- Companions: [python](../python/SKILL.md), [duckdb](../duckdb/SKILL.md), [databricks](../cloud-ops/references/databricks/GUIDE.md), [hf](../cloud-ops/references/hf.md).
