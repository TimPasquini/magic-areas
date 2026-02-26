"""Light control switch."""

from homeassistant.const import EntityCategory

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import SwitchBase


class LightControlSwitch(SwitchBase):
    """Switch to enable/disable light control."""

    feature_id = MagicAreasFeatures.LIGHT_GROUPS
    _attr_entity_category = EntityCategory.CONFIG


__all__ = ["LightControlSwitch"]
