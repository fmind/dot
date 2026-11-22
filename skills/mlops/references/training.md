---
name: training
description: "Pandera schema validation, leakage checks, and scikit-learn pipelines."
---

# Data and Model Training

Tabular defaults: [polars](polars.md) (`>=2.1.0`) frames, Pandera (`>=0.36.0`) schemas, and a scikit-learn (`>=1.9.1`) `Pipeline` baseline ([pipeline.py](../templates/pipeline.py)); keep any framework the project already chose.

- **Use `pandera.pandas` on pandas**: install `uv add 'pandera[pandas]'` and `import pandera.pandas as pa` (top-level `pandera` emits `FutureWarning` under strict warning filters).
- **Derive splits from the deployment question**: treat the bike reference's two-month temporal split, schemas, and thresholds as examples only; use chronological splits with horizon/embargo gaps (`TimeSeriesSplit(gap=...)`) when label feedback is delayed, and keep entity groups (`user_id`, `account_id`) disjoint across train and evaluation.
- **Beat a trivial baseline & keep serialization safe**: benchmark every model against a deterministic heuristic or `DummyRegressor`/`DummyClassifier` baseline first (`pipeline.py` emits `baseline_rmse`). Load serialized model artifacts only from trusted registries and prefer weight-only formats (`safetensors`, ONNX) over `pickle`/`cloudpickle` across trust boundaries.
- **Tabular GBDT & HPO**: beat the simple scikit-learn baseline first, then layer `lightgbm>=4.7.0` or `xgboost` with early stopping on a clean validation fold. Run Optuna (`optuna>=5.1.0`) studies over grouped, stratified, or time-series CV (`--study-name`, `MedianPruner` / `HyperbandPruner`, SQLite/Postgres study storage) with zero leakage between fold transforms and tuning objective.
- **Reconcile grain, nulls, and sliced metrics**: verify primary-key uniqueness, pre/post-join row counts, and `null` vs floating `NaN` semantics before fitting; report sliced/cohort metrics, worst-group regressions, and probability calibration alongside aggregate scores.
- **Export deterministic evaluation plots**: render cohort comparisons and threshold sweeps with `altair>=6.3.0` plus `vl-convert-python` (static SVG/PNG without a browser), and dense ROC, PR, calibration, or residual diagnostics with `matplotlib>=3.11.2` ([diagrams-as-code](../../diagrams-as-code/SKILL.md)).

Tracking: [experiments](experiments.md) · Registry evaluation/promotion: [model-delivery](model-delivery.md).

## Documentation

- [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) · [releases](https://scikit-learn.org/stable/whats_new.html) · [LightGBM docs](https://lightgbm.readthedocs.io/) · [Optuna docs](https://optuna.readthedocs.io/) · [Pandera models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [Altair](https://altair-viz.github.io/) · [Matplotlib](https://matplotlib.org/stable/) · [Pandera releases](https://github.com/unionai-oss/pandera/releases).
