---
name: training
description: "Validate Polars or pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines."
---

# Data and Model Training

Tabular defaults: [polars](polars.md) frames, Pandera schemas, and a scikit-learn `Pipeline` baseline; keep any framework the project already chose.

- **Use `pandera.pandas` on pandas**: install `uv add 'pandera[pandas]'` and `import pandera.pandas as pa` (top-level `pandera` emits `FutureWarning` under strict warning filters).
- **Derive splits from the deployment question**: treat the bike reference's two-month temporal split, schemas, and thresholds as examples only.
- **Keep `skops` serialization**: outside Databricks, MLflow 3.14+ logs scikit-learn models via `skops` (rejecting unreviewed custom callables/types); allowlist reviewed types in `skops_trusted_types` rather than falling back to `cloudpickle`, and load only from trusted registries (`MLmodel` records `skops_trusted_types`).

Tracking: [experiments](experiments.md) · Registry evaluation/promotion: [model-delivery](model-delivery.md).

## Documentation

- [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) · [releases](https://scikit-learn.org/stable/whats_new.html) · [Pandera models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [releases](https://github.com/unionai-oss/pandera/releases).
