"""Presence hold switch."""

from homeassistant.const import EntityCategory

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.config_keys import (
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoPresenceHold,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
)
from custom_components.magic_areas.switch.base import ResettableSwitchBase


class PresenceHoldSwitch(ResettableSwitchBase):
    """Switch to enable/disable presence hold."""

    feature_info = MagicAreasFeatureInfoPresenceHold()
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, area: MagicArea) -> None:
        """Initialize the switch."""

        # Get timeout from feature config before calling parent __init__
        # We can't use self.get_feature_config() here since self doesn't exist yet
        feature_config = area.feature_config(MagicAreasFeatures.PRESENCE_HOLD)
        timeout = feature_config.get(
            CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
        )

        ResettableSwitchBase.__init__(self, area, timeout=timeout)
