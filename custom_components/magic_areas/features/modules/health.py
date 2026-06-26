"""Health monitoring feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.group.binary_sensor import CONF_ALL
from homeassistant.components.group.const import CONF_HIDE_MEMBERS
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.aggregates import (
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import HEALTH_OPTION_KEYS

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


HEALTH_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.HEALTH,
    keys_and_validators=((HEALTH_OPTION_KEYS[0], [str]),),
)

GROUP_DOMAIN = "group"


class HealthFeatureModule(BaseFeatureModule):
    """Feature module for health monitoring."""

    id = MagicAreasFeatures.HEALTH
    domains = {BINARY_SENSOR_DOMAIN}
    feature_schema = HEALTH_FEATURE_SCHEMA

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the health feature."""
        return []

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA health group helper."""
        policy = build_default_aggregate_selection_policy()
        spec = policy.health_spec(
            AggregatePolicyContext(
                entities_by_domain=data.entities,
                feature_configs=data.feature_configs,
                enabled_features=data.enabled_features,
            )
        )
        if spec is None:
            return []

        title = f"Magic Areas Health {area_config.name} Health Problem"
        return [
            ConfigEntryHelperSurface(
                unique_id=build_managed_surface_unique_id(
                    entry_id=area_config.hass_config.entry_id,
                    area_id=area_config.id,
                    feature_id=MagicAreasFeatures.HEALTH,
                    surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
                    role="health_problem",
                ),
                domain=GROUP_DOMAIN,
                title=title,
                options={
                    "group_type": BINARY_SENSOR_DOMAIN,
                    CONF_NAME: title,
                    CONF_ENTITIES: list(spec.entity_ids),
                    CONF_HIDE_MEMBERS: False,
                    CONF_ALL: False,
                },
                area_id=area_config.id,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}",
                ),
                device_name=area_config.name,
                device_class=BinarySensorDeviceClass.PROBLEM,
            )
        ]


__all__ = ["HealthFeatureModule"]
