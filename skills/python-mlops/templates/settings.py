"""Typed configuration loader combining Pydantic Settings YAML layering with strict validation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class JobConfig(BaseSettings):
    """Validated ML job configuration."""

    model_config = SettingsConfigDict(extra="forbid")

    alpha: float = Field(default=1.0, gt=0.0)
    seed: int = Field(default=42, ge=0)
    test_fraction: float = Field(default=0.25, gt=0.0, lt=1.0)
    target_column: str = Field(default="target", min_length=1)


def _apply_override(data: dict[str, Any], override: str) -> None:
    key_path, separator, value = override.partition("=")
    if not separator or not key_path.strip():
        raise ValueError(f"override must use key=value format: {override!r}")
    parts = [part.strip() for part in key_path.split(".")]
    if any(not part for part in parts):
        raise ValueError(f"override key path contains an empty segment: {key_path!r}")
    cursor: dict[str, Any] = data
    for part in parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            nested = {}
            cursor[part] = nested
        cursor = nested
    cursor[parts[-1]] = value


def load_config(
    config_paths: Sequence[Path] = (),
    overrides: Sequence[str] = (),
) -> JobConfig:
    """Load and deep-merge YAML configs, apply CLI key=value overrides, and validate strictly."""
    merged: dict[str, Any] = {}
    if config_paths:
        source = YamlConfigSettingsSource(JobConfig, yaml_file=list(config_paths), deep_merge=True)
        merged = dict(source.yaml_data)
    for item in overrides:
        _apply_override(merged, item)
    return JobConfig.model_validate(merged)
