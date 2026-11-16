from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from pandera.errors import SchemaError
from pydantic import ValidationError

from <package>.pipeline import prepare_features, train_and_predict
from <package>.settings import JobConfig, load_config


def test_load_config_merges_yaml_and_overrides(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    base.write_text("alpha: 0.5\nseed: 7\n", encoding="utf-8")

    config = load_config([base], overrides=["alpha=2.5"])

    assert config == JobConfig(alpha=2.5, seed=7, target_column="target")


def test_load_config_rejects_unknown_keys(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("alpha: 1.0\nunexpected_key: true\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config([bad])


def test_prepare_features_rejects_out_of_bounds_values() -> None:
    invalid = pl.LazyFrame({"x1": [-1.0, 2.0], "x2": [0.5, 1.5]})

    with pytest.raises(SchemaError):
        prepare_features(invalid)


def test_train_and_predict_is_deterministic() -> None:
    frame = pl.LazyFrame({"x1": [1.0, 2.0, 3.0], "x2": [0.5, 1.5, 2.5]})
    target = pl.Series("target", [1.0, 2.0, 3.0])

    first = train_and_predict(frame, target, alpha=0.5)
    second = train_and_predict(frame, target, alpha=0.5)

    assert len(first) == 3
    assert first == second
