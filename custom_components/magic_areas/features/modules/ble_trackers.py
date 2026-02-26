"""BLE tracker feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_ble_tracker_sensor,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.config_keys import CONF_BLE_TRACKER_ENTITIES
from custom_components.magic_areas.defaults import DEFAULT_BLE_TRACKER_ENTITIES

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


BLE_TRACKER_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_BLE_TRACKER_ENTITIES, default=DEFAULT_BLE_TRACKER_ENTITIES
        ): cv.entity_ids,
    },
    extra=vol.REMOVE_EXTRA,
)


class BLETrackersFeatureModule(BaseFeatureModule):
    """Feature module for BLE trackers."""

    id = MagicAreasFeatures.BLE_TRACKER
    domains = {BINARY_SENSOR_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return BLE_TRACKER_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.BLE_TRACKER in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the BLE tracker feature."""
        entities = create_ble_tracker_sensor(data, area_config, coordinator)
        return cast(list[Entity], entities)

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.BLE_TRACKER,
                step_id="feature_conf_ble_trackers",
                schema=BLE_TRACKER_FEATURE_SCHEMA,
            )
        ]


__all__ = ["BLETrackersFeatureModule"]
