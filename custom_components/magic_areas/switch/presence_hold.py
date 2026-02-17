"""Presence hold switch."""

from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.config_keys import (
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoPresenceHold,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import ResettableSwitchBase


class PresenceHoldSwitch(ResettableSwitchBase):
    """Switch to enable/disable presence hold."""

    feature_info = MagicAreasFeatureInfoPresenceHold()
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the switch."""

        # Get timeout from coordinator snapshot (single source of truth)
        timeout = DEFAULT_PRESENCE_HOLD_TIMEOUT
        if coordinator.data and coordinator.data.feature_configs:
            feature_config = coordinator.data.feature_configs.get(
                MagicAreasFeatures.PRESENCE_HOLD, {}
            )
            timeout = feature_config.get(
                CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
            )

        ResettableSwitchBase.__init__(self, area_config, coordinator, timeout=timeout)
