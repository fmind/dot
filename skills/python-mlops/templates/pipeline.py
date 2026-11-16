"""Lazy Polars feature preparation, Pandera validation, and scikit-learn pipeline baseline."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl
from pandera.typing.polars import Series
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class FeatureSchema(pa.DataFrameModel):
    """Validated numeric features handed from Polars to scikit-learn."""

    x1: Series[float] = pa.Field(ge=0.0)
    x2: Series[float]


def prepare_features(frame: pl.LazyFrame) -> pl.DataFrame:
    """Transform features lazily, materialize once, and validate schema bounds."""
    collected = frame.with_columns((pl.col("x1") * 2.0).alias("x1")).collect()
    return FeatureSchema.validate(collected)


def build_pipeline(*, alpha: float = 1.0) -> Pipeline:
    """Construct a scikit-learn pipeline that preserves Polars outputs across transforms."""
    return Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=alpha))]).set_output(transform="polars")


def train_and_predict(frame: pl.LazyFrame, target: pl.Series, *, alpha: float = 1.0) -> list[float]:
    """Validate features, fit the baseline pipeline, and return deterministic predictions."""
    features = prepare_features(frame)
    pipeline = build_pipeline(alpha=alpha)
    feature_frame = features.select("x1", "x2")
    pipeline.fit(feature_frame, target)
    return [float(value) for value in pipeline.predict(feature_frame).tolist()]
