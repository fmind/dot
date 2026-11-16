"""Leakage-free Polars preprocessing, Pandera row validation, and scikit-learn holdout evaluation."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl
from pandera.typing.polars import Series
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


def prepare_features(frame: pl.LazyFrame) -> pl.DataFrame:
    """Apply stateless row transforms, materialize once, and validate Pandera constraints."""
    collected = frame.with_columns((pl.col("x1") * 2.0).alias("x1")).collect()
    return FeatureSchema.validate(collected.select("x1", "x2"))


def build_pipeline(*, alpha: float = 1.0) -> Pipeline:
    """Construct a scikit-learn pipeline keeping fitted transforms out of global preprocessing."""
    return Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=alpha))]).set_output(transform="polars")


def train_and_evaluate(frame: pl.LazyFrame, config: JobConfig) -> tuple[Pipeline, dict[str, float]]:
    """Split train/holdout reproducibly, fit the pipeline on train only, and score the holdout split."""
    collected = frame.collect()
    features = prepare_features(collected.lazy())
    target = collected.get_column(config.target_column)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=config.test_fraction,
        random_state=config.seed,
    )
    pipeline = build_pipeline(alpha=config.alpha)
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    metrics = {
        "rmse": float(root_mean_squared_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
    }
    return pipeline, metrics


def predict(pipeline: Pipeline, frame: pl.LazyFrame) -> list[float]:
    """Run serving-safe inference using the exact same feature contract as training."""
    features = prepare_features(frame)
    return [float(value) for value in pipeline.predict(features).tolist()]
