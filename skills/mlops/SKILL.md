---
name: mlops
description: "Build Python ML/MLOps pipelines, notebooks, and KPI/A-B analytics: Polars, Pandera, scikit-learn, LightGBM, PyTorch, vLLM, MLflow, marimo, Airflow, Kaggle."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mlops
  created: "2026-11-22"
  updated: "2026-11-24"
---

# Python MLOps

Build ML workflows and statistical analyses from exploration to evaluated delivery, grounded in [reviewed MLOps repos](references/sources.md). Load the matching guide(s) (`marimo` for notebooks, `analytics` for KPI/A-B studies, keeping existing libraries/formats), confirm compute/registry targets before running jobs or promotions, and audit deliverables with `fmind-review-mlops`, `fmind-review-analytics`, and `fmind-review-data` (plus `fmind-review-visuals` on plots; [subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [analytics](references/analytics.md): Design and audit KPI analyses and A/B experiments: power, SRM, bias, causality, uncertainty.
- [gpu-and-serving](references/gpu-and-serving.md): PyTorch CUDA/CPU uv indexes, safetensors, and bounded vLLM GPU serving.
- [marimo](references/marimo.md): Reactive marimo Python notebooks and apps, export, and agent pairing.
- [ml-jobs](references/ml-jobs.md): Package notebooks into typed ML jobs and MLOps reference architectures.
- [mlflow](references/mlflow.md): Track MLflow experiments, lineage, and GenAI evals; evaluate, alias-promote, and roll back models.
- [orchestration-and-competitions](references/orchestration-and-competitions.md): Airflow DAGs with astro and Kaggle downloads, kernels, and submissions.
- [polars](references/polars.md): Polars lazy tabular pipelines; hand off to Pandera, scikit-learn, DuckDB.
- [training](references/training.md): Pandera schema validation, leakage checks, and scikit-learn pipelines.

<!-- guides:end -->

## Documentation

- [Source map](references/sources.md) (each guide links its upstream docs).
- Companions: [python](../python/SKILL.md), [sql](../sql/SKILL.md), [databricks](../cloud-ops/references/databricks/GUIDE.md), [hf](../cloud-ops/references/hf.md).
