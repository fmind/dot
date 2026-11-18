---
name: python-mlops
description: "Build Python ML pipelines: Polars, Pandera, scikit-learn, MLflow, marimo."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/python-mlops
  created: "2026-09-16"
  updated: "2026-11-17"
---

# Python MLOps

Build ML workflows from exploration to evaluated delivery, grounded in the [reviewed MLOps repositories](references/sources.md). Load the matching guide(s) for every active stage (`marimo` for notebooks, keeping existing libraries/formats), confirm permitted compute, tracking stores, and registry targets before running jobs or promotions, and audit pipelines with `fmind-review-mlops` and `fmind-review-data` (plus `fmind-review-figures` on plots; [subagent](../subagent/SKILL.md)).

## Task guides

<!-- guides:start -->

- [experiments](references/experiments.md): Track reproducible MLflow experiments, data lineage, metrics, model signatures, and bounded artifacts.
- [gpu-and-serving](references/gpu-and-serving.md): Configure PyTorch CUDA/CPU uv indexes, safetensors loading, and vLLM GPU serving with memory bounds.
- [marimo](references/marimo.md): Create, debug, convert, and export reactive marimo Python notebooks and apps, including agent pairing.
- [ml-jobs](references/ml-jobs.md): Turn notebook experiments into typed, configurable ML jobs; select the MLOps template or reference architecture.
- [model-delivery](references/model-delivery.md): Evaluate exact model versions, manage MLflow registry aliases, and verify batch inference and rollback.
- [orchestration-and-competitions](references/orchestration-and-competitions.md): Develop and test Airflow DAGs with astro and run Kaggle downloads, kernels, and submissions per project.
- [polars](references/polars.md): Transform tabular data with Polars lazy queries and expressions; hand frames to Pandera, scikit-learn, and DuckDB.
- [training](references/training.md): Validate Polars or pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines.

<!-- guides:end -->

## Documentation

- [Polars](https://docs.pola.rs/) · [obstore](https://developmentseed.org/obstore/latest/) · [Pandera](https://pandera.readthedocs.io/en/stable/) · [scikit-learn](https://scikit-learn.org/stable/) · [LightGBM](https://lightgbm.readthedocs.io/en/stable/) · [Optuna](https://optuna.readthedocs.io/en/stable/) · [Altair](https://altair-viz.github.io/) · [Matplotlib](https://matplotlib.org/stable/) · [MLflow](https://mlflow.org/docs/latest/) · [marimo](https://docs.marimo.io/) · [vLLM](https://docs.vllm.ai/en/latest/)
- Companions: [python-stack](../python-stack/SKILL.md), [duckdb](../duckdb/SKILL.md), [colab](../colab/SKILL.md), [databricks](../databricks/SKILL.md), [hf](../hf/SKILL.md).
