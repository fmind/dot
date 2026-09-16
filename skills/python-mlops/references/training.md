---
name: training
description: "Validate pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines."
---

# Data and Model Training

Use this guide for tabular prediction and reproducible model comparisons. Preserve an explicitly chosen framework; scikit-learn is the starting point for a conventional tabular baseline.

1. **Define the prediction contract**: target, unit of observation, prediction time, available features, metric direction, baseline, and cost of errors. Exclude features unavailable at prediction time, including future aggregates and target proxies.
1. **Validate incoming data**: use pandas with Pandera schemas for required columns, types, nullability, ranges, and domain constraints. Make coercion and extra-column policy deliberate. Verify input/target row identity, uniqueness, order, and join cardinality; independently valid frames can still pair the wrong rows. Report bounded diagnostics without private samples.
1. **Split before learning transformations**: reserve a final holdout and choose random, stratified, temporal, or group splits from the deployment question. Use the same row indices for features, labels, and groups. Time splits require sorted timestamps and a gap when feature/label windows overlap; repeated entities need group separation. Do not apply the reference bike dataset's two-month split to unrelated data.
1. **Fit the whole pipeline within each training fold**: place learned imputation, scaling, encoding, feature selection, and the estimator in a scikit-learn `Pipeline` with `ColumnTransformer` when appropriate. Fit on training rows; transform or predict on validation/holdout rows. Fit preprocessing again inside each cross-validation fold. Deterministic row-local transformations may precede splitting when they use only information available at prediction time.
1. **Bound tuning**: define search space, trials/folds, concurrency, memory, timeout, and random-state policy. Compare a simple baseline on identical folds. Tune using validation results; use the final holdout only for the agreed final assessment. Preserve uncertainty across folds/seeds instead of claiming a seed guarantees reproducibility.
1. **Verify the delivered predictor**: reload the saved preprocessing plus model artifact in the intended environment, predict a small held-out sample, and compare shape, row identity, dtypes, and values within an explicit tolerance. Exercise missing/extra columns and unseen categories according to the declared inference contract. For tracking use [experiments](experiments.md); for registry evaluation and promotion use [model-delivery](model-delivery.md).

## Validation evidence

Record data revision/digest, split boundaries or indices, pipeline parameters, environment lock, metrics with direction and comparison, and the reload result. Check that train/test groups or times obey the declared separation and that invalid schemas fail before fitting. A high score is not evidence that leakage checks passed.

## Documentation

- [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) · [model selection](https://scikit-learn.org/stable/model_selection.html) · [releases](https://scikit-learn.org/stable/whats_new.html).
- [Pandera dataframe models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [releases](https://github.com/unionai-oss/pandera/releases).
- [pandas user guide](https://pandas.pydata.org/docs/user_guide/index.html) · [releases](https://pandas.pydata.org/docs/whatsnew/index.html).
