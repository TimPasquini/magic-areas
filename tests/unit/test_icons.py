"""Tests for meta-area icon constants."""

from custom_components.magic_areas.components import MetaAreaIcons


def test_icon_constants() -> None:
    """Test icon constants are defined."""
    assert MetaAreaIcons.INTERIOR.value == "mdi:home-import-outline"
    assert MetaAreaIcons.EXTERIOR.value == "mdi:home-export-outline"
    assert MetaAreaIcons.GLOBAL.value == "mdi:home"
