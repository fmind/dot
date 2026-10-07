---
name: training
description: "Validate Polars or pandas data with Pandera, prevent leakage, and train, tune, and evaluate scikit-learn pipelines."
---

# Data and Model Training

Tabular prediction defaults: [polars](polars.md) frames, Pandera schemas, and a scikit-learn `Pipeline` baseline; preserve a framework the project already chose.

- **Import `pandera.pandas` for pandas**: install `uv add 'pandera[pandas]'` and `import pandera.pandas as pa`; the top-level pandas API emits a `FutureWarning` that fails strict warning filters.
- **Check row identity, not just schemas**: verify input/target alignment, uniqueness, and join cardinality; independently valid frames can still pair the wrong rows.
- **Never reuse the reference split blindly**: the bike example's two-month temporal split, schemas, and thresholds are examples; derive the split from the deployment question.
- **Keep the final holdout final**: tune on validation folds against a simple baseline on identical folds; touch the holdout once for the agreed assessment and report fold/seed spread, not a single seed.
- **Prove the reloaded artifact**: reload the saved preprocessing plus model in the target environment and compare predictions on a held-out sample within an explicit tolerance. A high score is not evidence that leakage checks passed.

Tracking belongs to [experiments](experiments.md); registry evaluation and promotion to [model-delivery](model-delivery.md).

## Documentation

- [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) · [releases](https://scikit-learn.org/stable/whats_new.html).
- [Pandera dataframe models](https://pandera.readthedocs.io/en/stable/dataframe_models.html) · [releases](https://github.com/pandera-dev/pandera/releases).
