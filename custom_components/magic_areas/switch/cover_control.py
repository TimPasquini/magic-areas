"""Cover control switch."""

from homeassistant.const import EntityCategory

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import SwitchBase


class CoverControlSwitch(SwitchBase):
    """Switch to enable/disable Magic Areas cover automation."""

    feature_id = MagicAreasFeatures.COVER_GROUPS
    _attr_entity_category = EntityCategory.CONFIG


__all__ = ["CoverControlSwitch"]
