"""Typed configuration loader combining OmegaConf YAML merging with strict Pydantic validation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from omegaconf import OmegaConf
from pydantic import BaseModel, ConfigDict, Field


class JobConfig(BaseModel):
    """Validated ML job configuration."""

    model_config = ConfigDict(extra="forbid")

    alpha: float = Field(default=1.0, gt=0.0)
    seed: int = Field(default=42, ge=0)
    target_column: str = "target"


def load_config(
    config_paths: Sequence[Path] = (),
    overrides: Sequence[str] = (),
) -> JobConfig:
    """Merge YAML config files in order, apply CLI dotlist overrides, and validate before side effects."""
    layers = [OmegaConf.load(path) for path in config_paths]
    if overrides:
        layers.append(OmegaConf.from_dotlist(list(overrides)))
    merged = OmegaConf.merge(*layers) if layers else OmegaConf.create({})
    resolved = OmegaConf.to_container(merged, resolve=True)
    return JobConfig.model_validate(resolved)
