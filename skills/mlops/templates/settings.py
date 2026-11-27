"""Typed configuration loader combining Pydantic Settings YAML layering with strict validation."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class JobConfig(BaseSettings):
    """Validated ML job configuration (ignores ambient OS env vars)."""

    model_config = SettingsConfigDict(extra="forbid")

    alpha: float = Field(default=1.0, gt=0.0)
    seed: int = Field(default=42, ge=0)
    test_fraction: float = Field(default=0.25, gt=0.0, lt=1.0)
    target_column: str = Field(default="target", min_length=1)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del settings_cls, env_settings, dotenv_settings, file_secret_settings
        return (init_settings,)


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
        if nested is None:
            nested = {}
            cursor[part] = nested
        elif not isinstance(nested, dict):
            raise ValueError(f"override path {key_path!r} collides with non-mapping key {part!r}")
        cursor = nested
    if isinstance(cursor.get(parts[-1]), dict):
        raise ValueError(f"scalar override cannot replace nested mapping at {key_path!r}")
    cursor[parts[-1]] = value


def load_config(
    config_paths: Sequence[Path] = (),
    overrides: Sequence[str] = (),
) -> JobConfig:
    """Load and deep-merge explicit YAML configs + CLI overrides deterministically (ignoring ambient env vars)."""
    merged: dict[str, Any] = {}
    if config_paths:
        for path in config_paths:
            if not path.is_file():
                raise FileNotFoundError(path)
        try:
            source = YamlConfigSettingsSource(
                JobConfig,
                yaml_file=list(config_paths),
                yaml_file_encoding="utf-8",
                deep_merge=True,
            )
        except (AttributeError, TypeError) as error:
            raise ValueError("YAML config root must be a mapping") from error
        if not isinstance(source.yaml_data, dict):
            raise ValueError("YAML config root must be a mapping")
        merged = deepcopy(source.yaml_data)
    for item in overrides:
        _apply_override(merged, item)
    return JobConfig.model_validate(merged)
