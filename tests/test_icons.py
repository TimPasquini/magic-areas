"""Tests for icon constants."""

from custom_components.magic_areas import icons


def test_icon_constants() -> None:
    """Test icon constants are defined."""
    assert icons.ICON_PRESENCE_HOLD == "mdi:car-brake-hold"
    assert icons.ICON_LIGHT_CONTROL == "mdi:lightbulb-auto-outline"
