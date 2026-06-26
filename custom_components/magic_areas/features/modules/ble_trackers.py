"""BLE tracker feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_ble_tracker_sensor,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import (
    BLE_TRACKER_OPTION_KEYS,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

BLE_TRACKER_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.BLE_TRACKER,
    keys_and_validators=((BLE_TRACKER_OPTION_KEYS[0], cv.entity_ids),),
)


class BLETrackersFeatureModule(BaseFeatureModule):
    """Feature module for BLE trackers."""

    id = MagicAreasFeatures.BLE_TRACKER
    domains = {BINARY_SENSOR_DOMAIN}
    feature_schema = BLE_TRACKER_FEATURE_SCHEMA
    feature_step_id = "feature_conf_ble_trackers"
    supports_meta_area = False
    supports_global_meta_area = False

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the BLE tracker feature."""
        entities: list[Entity] = list(
            create_ble_tracker_sensor(data, area_config, coordinator)
        )
        return entities


__all__ = ["BLETrackersFeatureModule"]
