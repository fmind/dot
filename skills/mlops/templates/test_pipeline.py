from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from pandera.errors import SchemaError
from pydantic import ValidationError

from <package>.pipeline import predict, prepare_features, train_and_evaluate
from <package>.settings import JobConfig, load_config


def test_load_config_merges_yaml_and_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHA", "99.0")
    monkeypatch.setenv("SEED", "999")
    assert JobConfig() == JobConfig(alpha=1.0, seed=42, test_fraction=0.25, target_column="target")

    base = tmp_path / "base.yaml"
    overlay = tmp_path / "overlay.yaml"
    base.write_text("alpha: 0.5\nseed: 7\ntest_fraction: 0.2\n", encoding="utf-8")
    overlay.write_text("seed: 9\n", encoding="utf-8")

    config = load_config([base, overlay], overrides=["alpha=2.5"])

    assert config == JobConfig(alpha=2.5, seed=9, test_fraction=0.2, target_column="target")


def test_load_config_rejects_unknown_keys(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("alpha: 1.0\nunexpected_key: true\n", encoding="utf-8")
    non_mapping = tmp_path / "list.yaml"
    non_mapping.write_text("- a\n- b\n", encoding="utf-8")
    nested = tmp_path / "nested.yaml"
    nested.write_text("section:\n  key: 1\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config([bad])

    with pytest.raises(ValueError, match="mapping"):
        load_config([non_mapping])

    with pytest.raises(ValueError, match="nested mapping"):
        load_config([nested], overrides=["section=scalar"])

    with pytest.raises(ValueError, match="non-mapping"):
        load_config([bad], overrides=["alpha.sub=1"])

    with pytest.raises(ValueError, match="key=value"):
        load_config(overrides=["missing_equals"])

    with pytest.raises(ValueError, match="empty segment"):
        load_config(overrides=["a..b=1"])

    with pytest.raises(FileNotFoundError):
        load_config([tmp_path / "missing.yaml"])


def test_prepare_features_rejects_out_of_bounds_values() -> None:
    invalid = pl.LazyFrame({"x1": [-1.0, 2.0], "x2": [0.5, 1.5]})

    with pytest.raises(SchemaError):
        prepare_features(invalid)


@pytest.mark.parametrize("bad_target", [None, float("nan"), float("inf")])
def test_train_and_evaluate_rejects_non_finite_or_null_target(bad_target: float | None) -> None:
    dataset = pl.LazyFrame(
        {
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "x2": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
            "target": [1.0, 2.0, bad_target, 4.0, 5.0, 6.0, 7.0, 8.0],
        }
    )

    with pytest.raises(SchemaError):
        train_and_evaluate(dataset, JobConfig(seed=7))


def test_train_and_evaluate_uses_holdout_split_and_serves_consistently() -> None:
    dataset = pl.LazyFrame(
        {
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "x2": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
            "target": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        }
    )
    config = JobConfig(alpha=0.5, seed=7, test_fraction=0.25, target_column="target")

    first_model, first_metrics = train_and_evaluate(dataset, config)
    second_model, second_metrics = train_and_evaluate(dataset, config)

    assert first_metrics == pytest.approx(second_metrics)
    assert first_metrics["rmse"] < first_metrics["baseline_rmse"]
    assert first_metrics["rmse"] < 0.5
    preds_a = predict(first_model, dataset.select("x1", "x2").limit(3))
    preds_b = predict(second_model, dataset.select("x1", "x2").limit(3))
    assert preds_a == pytest.approx(preds_b)
    assert len(preds_a) == 3
