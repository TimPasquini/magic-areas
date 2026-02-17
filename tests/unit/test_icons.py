"""Tests for icon constants."""

from custom_components.magic_areas.icons import FeatureIcons, MetaAreaIcons


def test_icon_constants() -> None:
    """Test icon constants are defined."""
    assert FeatureIcons.PRESENCE_HOLD_SWITCH == "mdi:car-brake-hold"
    assert FeatureIcons.LIGHT_CONTROL_SWITCH == "mdi:lightbulb-auto-outline"
    assert MetaAreaIcons.INTERIOR == "mdi:home-import-outline"
    assert MetaAreaIcons.EXTERIOR == "mdi:home-export-outline"
    assert MetaAreaIcons.GLOBAL == "mdi:home"
