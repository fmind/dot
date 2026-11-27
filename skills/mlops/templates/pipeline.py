"""Leakage-free Polars preprocessing, Pandera row validation, and scikit-learn holdout evaluation."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl
from pandera.typing.polars import Series
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .settings import JobConfig


class FeatureSchema(pa.DataFrameModel):
    """Row-wise feature schema enforced identically at training and serving boundaries."""

    x1: Series[float] = pa.Field(ge=0.0)
    x2: Series[float]


class TargetSchema(pa.DataFrameModel):
    """Target contract enforced at the training boundary (non-null and finite)."""

    target: Series[float] = pa.Field(nullable=False)

    @pa.check("target")
    @classmethod
    def _target_is_finite(cls, data: pa.PolarsData) -> pl.LazyFrame:
        return data.lazyframe.select(pl.col(data.key).is_finite())


def prepare_features(frame: pl.LazyFrame) -> pl.DataFrame:
    """Apply stateless row transforms, materialize once, and validate Pandera constraints."""
    collected = frame.with_columns((pl.col("x1") * 2.0).alias("x1")).select("x1", "x2").collect()
    return FeatureSchema.validate(collected)


def validate_target(frame: pl.DataFrame, target_column: str) -> pl.Series:
    """Validate the configured target column as non-null and finite at the Pandera boundary."""
    validated = TargetSchema.validate(frame.select(pl.col(target_column).alias("target")))
    return validated.get_column("target").alias(target_column)


def build_pipeline(*, alpha: float = 1.0) -> Pipeline:
    """Construct a scikit-learn pipeline keeping fitted transforms out of global preprocessing."""
    return Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=alpha))]).set_output(transform="polars")


def train_and_evaluate(frame: pl.LazyFrame, config: JobConfig) -> tuple[Pipeline, dict[str, float]]:
    """Split train/holdout reproducibly, fit the pipeline on train only, and score the holdout split."""
    collected = frame.collect()
    # Random split fits i.i.d. rows only; use temporal splits (TimeSeriesSplit(gap=...)) on
    # time-indexed data and group-disjoint splitters (GroupShuffleSplit/GroupKFold) on entity data.
    raw_train, raw_test = train_test_split(
        collected,
        test_size=config.test_fraction,
        random_state=config.seed,
    )
    x_train = prepare_features(raw_train.lazy())
    y_train = validate_target(raw_train, config.target_column)
    x_test = prepare_features(raw_test.lazy())
    y_test = validate_target(raw_test, config.target_column)
    baseline = DummyRegressor(strategy="mean").fit(x_train, y_train)
    pipeline = build_pipeline(alpha=config.alpha)
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    metrics = {
        "baseline_rmse": float(root_mean_squared_error(y_test, baseline.predict(x_test))),
        "rmse": float(root_mean_squared_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
    }
    return pipeline, metrics


def predict(pipeline: Pipeline, frame: pl.LazyFrame) -> list[float]:
    """Run serving-safe inference using the exact same feature contract as training."""
    features = prepare_features(frame)
    return [float(value) for value in pipeline.predict(features).tolist()]
