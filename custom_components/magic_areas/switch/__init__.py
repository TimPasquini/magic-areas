"""Platform file for Magic Area's switch entities."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import MagicAreasFeatureInfoLightGroups
from custom_components.magic_areas.switch.base import SwitchBase
from custom_components.magic_areas.switch.climate_control import ClimateControlSwitch
from custom_components.magic_areas.switch.fan_control import FanControlSwitch
from custom_components.magic_areas.switch.media_player_control import (
    MediaPlayerControlSwitch,
)
from custom_components.magic_areas.switch.presence_hold import PresenceHoldSwitch
from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area switch config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping switch setup; coordinator data unavailable")
        return
    area_config = data.area_config
    coordinator = runtime_data.coordinator

    switch_entities: list[SwitchBase] = []

    if MagicAreasFeatures.PRESENCE_HOLD in data.enabled_features and not area_config.is_meta():
        try:
            switch_entities.append(PresenceHoldSwitch(area_config, coordinator))
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading presence hold switch: %s", area_config.name, str(e)
            )

    if MagicAreasFeatures.LIGHT_GROUPS in data.enabled_features and not area_config.is_meta():
        try:
            switch_entities.append(LightControlSwitch(area_config, coordinator))
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading light control switch: %s", area_config.name, str(e)
            )

    if MagicAreasFeatures.MEDIA_PLAYER_GROUPS   in data.enabled_features and not area_config.is_meta():
        try:
            switch_entities.append(MediaPlayerControlSwitch(area_config, coordinator))
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading media player control switch: %s", area_config.name, str(e)
            )

    if MagicAreasFeatures.FAN_GROUPS in data.enabled_features and not area_config.is_meta():
        try:
            switch_entities.append(FanControlSwitch(area_config, coordinator))
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error("%s: Error loading fan control switch: %s", area_config.name, str(e))

    if MagicAreasFeatures.CLIMATE_CONTROL  in data.enabled_features:
        try:
            switch_entities.append(ClimateControlSwitch(area_config, coordinator))
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading climate control switch: %s", area_config.name, str(e)
            )

    if switch_entities:
        async_add_entities(switch_entities)

    if SWITCH_DOMAIN in data.magic_entities:
        cleanup_removed_entries(
            hass, switch_entities, data.magic_entities[SWITCH_DOMAIN]
        )


class LightControlSwitch(SwitchBase):
    """Switch to enable/disable light control."""

    feature_info = MagicAreasFeatureInfoLightGroups()
    _attr_entity_category = EntityCategory.CONFIG
