"""Platform file for Magic Area's switch entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)
from custom_components.magic_areas.features.config.readers import (
    presence_hold_config,
)
from custom_components.magic_areas.switch.base import SwitchBase
from custom_components.magic_areas.switch.base import ResettableSwitchBase
from custom_components.magic_areas.switch.climate_control import (  # noqa: F401
    ClimateControlSwitch,
)
from custom_components.magic_areas.switch.fan_control import FanControlSwitch  # noqa: F401
from custom_components.magic_areas.switch.media_player_control import (  # noqa: F401
    MediaPlayerControlSwitch,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0

__all__ = [
    "ClimateControlSwitch",
    "FanControlSwitch",
    "LightControlSwitch",
    "MediaPlayerControlSwitch",
    "PresenceHoldSwitch",
]


class LightControlSwitch(SwitchBase):
    """Switch to enable/disable light control."""

    feature_id = MagicAreasFeatures.LIGHT_GROUPS
    _attr_entity_category = EntityCategory.CONFIG


class PresenceHoldSwitch(ResettableSwitchBase):
    """Switch to enable/disable presence hold."""

    feature_id = MagicAreasFeatures.PRESENCE_HOLD
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, area_config: AreaConfig, coordinator: MagicAreasCoordinator
    ) -> None:
        """Initialize the switch."""
        feature_configs = coordinator.data.feature_configs if coordinator.data else {}
        timeout = presence_hold_config(feature_configs).timeout
        ResettableSwitchBase.__init__(self, area_config, coordinator, timeout=timeout)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area switch config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=SWITCH_DOMAIN,
        logger=_LOGGER,
    )
