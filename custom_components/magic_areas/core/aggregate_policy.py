"""Canonical aggregate selection policy interfaces."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN

from custom_components.magic_areas.core.aggregate_selection import (
    build_binary_sensor_aggregates,
    build_health_sensor_spec,
    build_sensor_aggregates,
)
from custom_components.magic_areas.core.aggregate_specs import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@dataclass(frozen=True, slots=True)
class AggregatePolicyContext:
    """Canonical input context for aggregate selection policies."""

    entities_by_domain: dict[str, list[dict[str, str]]]
    feature_configs: Mapping[str | MagicAreasFeatures, Mapping[str, Any]]
    enabled_features: Collection[str | MagicAreasFeatures]


class AggregateKind(StrEnum):
    """Kinds of aggregate definitions produced by policy."""

    STANDARD = "standard"
    HEALTH = "health"


@dataclass(frozen=True, slots=True)
class AggregateDefinition:
    """Canonical aggregate definition shared by all aggregate consumers."""

    domain: str
    device_class: str
    entity_ids: tuple[str, ...]
    kind: AggregateKind = AggregateKind.STANDARD
    unit_of_measurement: str | None = None


class AggregateSelectionPolicy(Protocol):
    """Policy interface for aggregate selection."""

    def aggregate_definitions(
        self, context: AggregatePolicyContext
    ) -> list[AggregateDefinition]:
        """Return all aggregate definitions for the given context."""

    def sensor_specs(self, context: AggregatePolicyContext) -> list[SensorAggregateSpec]:
        """Return sensor aggregate specs for the given context."""

    def binary_sensor_specs(
        self, context: AggregatePolicyContext
    ) -> list[BinarySensorAggregateSpec]:
        """Return binary-sensor aggregate specs for the given context."""

    def health_spec(self, context: AggregatePolicyContext) -> BinarySensorAggregateSpec | None:
        """Return health aggregate spec for the given context."""


class DefaultAggregateSelectionPolicy:
    """Default aggregate selection policy backed by current selection helpers."""

    def aggregate_definitions(
        self, context: AggregatePolicyContext
    ) -> list[AggregateDefinition]:
        """Return canonical aggregate definitions from current selection logic."""
        definitions: list[AggregateDefinition] = []

        for spec in self.sensor_specs(context):
            definitions.append(
                AggregateDefinition(
                    domain=SENSOR_DOMAIN,
                    device_class=spec.device_class,
                    entity_ids=tuple(spec.entity_ids),
                    unit_of_measurement=spec.unit_of_measurement,
                )
            )

        for binary_spec in self.binary_sensor_specs(context):
            definitions.append(
                AggregateDefinition(
                    domain=BINARY_SENSOR_DOMAIN,
                    device_class=binary_spec.device_class,
                    entity_ids=tuple(binary_spec.entity_ids),
                )
            )

        health_spec = self.health_spec(context)
        if health_spec:
            definitions.append(
                AggregateDefinition(
                    domain=BINARY_SENSOR_DOMAIN,
                    device_class=health_spec.device_class,
                    entity_ids=tuple(health_spec.entity_ids),
                    kind=AggregateKind.HEALTH,
                )
            )

        return definitions

    def sensor_specs(self, context: AggregatePolicyContext) -> list[SensorAggregateSpec]:
        """Return sensor aggregate specs from current selection logic."""
        return build_sensor_aggregates(
            entities_by_domain=context.entities_by_domain,
            feature_configs=context.feature_configs,
            enabled_features=context.enabled_features,
        )

    def binary_sensor_specs(
        self, context: AggregatePolicyContext
    ) -> list[BinarySensorAggregateSpec]:
        """Return binary-sensor aggregate specs from current selection logic."""
        return build_binary_sensor_aggregates(
            entities_by_domain=context.entities_by_domain,
            feature_configs=context.feature_configs,
            enabled_features=context.enabled_features,
        )

    def health_spec(self, context: AggregatePolicyContext) -> BinarySensorAggregateSpec | None:
        """Return health aggregate spec from current selection logic."""
        return build_health_sensor_spec(
            entities_by_domain=context.entities_by_domain,
            feature_configs=context.feature_configs,
            enabled_features=context.enabled_features,
        )


def build_default_aggregate_selection_policy() -> AggregateSelectionPolicy:
    """Build the default aggregate selection policy."""
    return DefaultAggregateSelectionPolicy()
