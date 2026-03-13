"""Tests for icon constants."""

from custom_components.magic_areas.components import FeatureIcons, MetaAreaIcons


def test_icon_constants() -> None:
    """Test icon constants are defined."""
    assert FeatureIcons.PRESENCE_HOLD_SWITCH.value == "mdi:car-brake-hold"
    assert FeatureIcons.LIGHT_CONTROL_SWITCH.value == "mdi:lightbulb-auto-outline"
    assert MetaAreaIcons.INTERIOR.value == "mdi:home-import-outline"
    assert MetaAreaIcons.EXTERIOR.value == "mdi:home-export-outline"
    assert MetaAreaIcons.GLOBAL.value == "mdi:home"
