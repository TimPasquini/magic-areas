"""Declarative feature registry for Magic Areas config flows.

This file centralizes per-feature configuration metadata so OptionsFlowHandler
can act as a generic dispatcher instead of a god class.
"""

from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureConfigStep
from custom_components.magic_areas.features.registry import (
    FEATURE_REGISTRY as RUNTIME_FEATURE_REGISTRY,
)


@dataclass
class FeatureConfig:
    """Declarative description of a configurable feature."""

    name: MagicAreasFeatures
    schema: vol.Schema | None = None
    merge_options: bool = False
    next_step: str | None = None


def _build_feature_registry() -> dict[MagicAreasFeatures, FeatureConfig]:
    registry: dict[MagicAreasFeatures, FeatureConfig] = {}
    for module in RUNTIME_FEATURE_REGISTRY.modules():
        for step in module.config_flow_steps():
            if step.step_id != f"feature_conf_{step.feature}":
                continue
            registry[step.feature] = _to_feature_config(step)
    return registry


def _to_feature_config(step: FeatureConfigStep) -> FeatureConfig:
    return FeatureConfig(
        name=step.feature,
        schema=step.schema,
        merge_options=step.merge_options,
        next_step=step.next_step,
    )


FEATURE_REGISTRY: dict[MagicAreasFeatures, FeatureConfig] = _build_feature_registry()


__all__ = ["FeatureConfig", "FEATURE_REGISTRY"]
