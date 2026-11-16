---
name: training
description: "Validate Polars or pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines."
---

# Data and Model Training

Tabular defaults: [polars](polars.md) (`>=2.1.0`) frames, Pandera (`>=0.36.0`) schemas, and a scikit-learn (`>=1.9.1`) `Pipeline` baseline ([pipeline.py](../templates/pipeline.py)); keep any framework the project already chose.

- **Use `pandera.pandas` on pandas**: install `uv add 'pandera[pandas]'` and `import pandera.pandas as pa` (top-level `pandera` emits `FutureWarning` under strict warning filters).
- **Derive splits from the deployment question**: treat the bike reference's two-month temporal split, schemas, and thresholds as examples only.
- **Keep `skops` serialization**: outside Databricks, MLflow 3.14+ logs scikit-learn models via `skops` (rejecting unreviewed custom callables/types); allowlist reviewed types in `skops_trusted_types` rather than falling back to `cloudpickle`, and load only from trusted registries (`MLmodel` records `skops_trusted_types`).
- **Tabular GBDT & HPO**: beat the simple scikit-learn baseline first, then layer `lightgbm>=4.7.0` or `xgboost` with early stopping on a clean validation fold. Run Optuna (`optuna>=5.1.0`) studies over grouped, stratified, or time-series CV (`--study-name`, `MedianPruner` / `HyperbandPruner`, SQLite/Postgres study storage) with zero leakage between fold transforms and tuning objective.

Tracking: [experiments](experiments.md) · Registry evaluation/promotion: [model-delivery](model-delivery.md).

## Documentation

- [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) · [releases](https://scikit-learn.org/stable/whats_new.html) · [LightGBM docs](https://lightgbm.readthedocs.io/) · [Optuna docs](https://optuna.readthedocs.io/) · [Pandera models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [releases](https://github.com/unionai-oss/pandera/releases).
