"""Aggregates feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.group.binary_sensor import CONF_ALL
from homeassistant.components.group.const import CONF_HIDE_MEMBERS
from homeassistant.components.group.const import CONF_IGNORE_NON_NUMERIC
from homeassistant.components.group.sensor import ATTR_MEAN, ATTR_SUM
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_ENTITIES, CONF_NAME, CONF_TYPE

from custom_components.magic_areas.binary_sensor import (
    create_illuminance_threshold,
)
from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.aggregates import (
    AggregateDefinition,
    AggregatePolicyContext,
    aggregate_managed_surface_unique_id,
    build_default_aggregate_selection_policy,
    register_aggregate_definitions,
)
from custom_components.magic_areas.core.aggregates import AggregateKind
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceOptionValue,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import AGGREGATES_OPTION_KEYS
from custom_components.magic_areas.policy import AGGREGATE_MODE_ALL, AGGREGATE_MODE_SUM

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


AGGREGATE_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.AGGREGATES,
    keys_and_validators=(
        (AGGREGATES_OPTION_KEYS[0], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[1], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[2], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[3], [str]),
        (AGGREGATES_OPTION_KEYS[4], [str]),
    ),
)

GROUP_DOMAIN = "group"


class AggregatesFeatureModule(BaseFeatureModule):
    """Feature module for aggregates."""

    id = MagicAreasFeatures.AGGREGATES
    domains = {"sensor", "binary_sensor"}
    feature_schema = AGGREGATE_FEATURE_SCHEMA

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the aggregates feature."""
        definitions = _aggregate_definitions(data)
        register_aggregate_definitions(
            group_registry=data.group_registry,
            area_id=area_config.id,
            definitions=definitions,
            owner_entry_id=area_config.hass_config.entry_id,
        )
        entities: list[Entity] = []

        threshold_entity = create_illuminance_threshold(
            coordinator.hass, data, area_config, coordinator
        )
        if threshold_entity:
            entities.append(threshold_entity)

        return entities

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA aggregate group helpers."""
        return [
            _aggregate_surface(area_config=area_config, definition=definition)
            for definition in _aggregate_definitions(data)
            if definition.kind is AggregateKind.STANDARD
        ]


def _aggregate_definitions(data: MagicAreasData) -> list[AggregateDefinition]:
    """Return aggregate definitions for current coordinator data."""
    policy = build_default_aggregate_selection_policy()
    return policy.aggregate_definitions(
        AggregatePolicyContext(
            entities_by_domain=data.entities,
            feature_configs=data.feature_configs,
            enabled_features=data.enabled_features,
        )
    )


def _aggregate_surface(
    *,
    area_config: AreaConfig,
    definition: AggregateDefinition,
) -> ConfigEntryHelperSurface:
    """Build one native group helper surface for an aggregate definition."""
    title = (
        f"Magic Areas Aggregates {area_config.name} "
        f"Aggregate {definition.device_class.replace('_', ' ').title()}"
    )
    options: dict[str, ManagedSurfaceOptionValue] = {
        "group_type": definition.domain,
        CONF_NAME: title,
        CONF_ENTITIES: list(definition.entity_ids),
        CONF_HIDE_MEMBERS: False,
    }
    if definition.domain == SENSOR_DOMAIN:
        options[CONF_IGNORE_NON_NUMERIC] = True
        options[CONF_TYPE] = (
            ATTR_SUM if definition.device_class in AGGREGATE_MODE_SUM else ATTR_MEAN
        )
    elif definition.domain == BINARY_SENSOR_DOMAIN:
        options[CONF_ALL] = definition.device_class in AGGREGATE_MODE_ALL

    return ConfigEntryHelperSurface(
        unique_id=aggregate_managed_surface_unique_id(
            entry_id=area_config.hass_config.entry_id,
            area_id=area_config.id,
            definition=definition,
        ),
        domain=GROUP_DOMAIN,
        title=title,
        options=options,
        area_id=area_config.id,
        device_identifier=(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}"),
        device_name=area_config.name,
    )


__all__ = [
    "AggregatesFeatureModule",
]
