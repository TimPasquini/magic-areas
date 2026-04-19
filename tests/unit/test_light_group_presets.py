"""Tests for light-group preset declarations and schema defaults."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_FEATURE_SCHEMA,
    LIGHT_GROUP_PRESETS,
    get_light_group_preset,
)


def test_light_group_preset_categories_are_unique() -> None:
    """Preset declarations should define unique category keys."""
    categories = [preset.category for preset in LIGHT_GROUP_PRESETS]
    assert len(categories) == len(set(categories))


def test_light_group_schema_defaults_follow_preset_defaults() -> None:
    """Feature schema defaults should be generated from preset declarations."""
    defaults = LIGHT_GROUP_FEATURE_SCHEMA({})

    for preset in LIGHT_GROUP_PRESETS:
        assert defaults[preset.category] == []
        assert defaults[preset.states_key] == list(preset.default_states)
        assert defaults[preset.act_on_key] == list(preset.default_act_on)

    assert defaults[LIGHT_GROUP_PRESETS[0].states_key] == [AreaStates.OCCUPIED]
    assert LIGHT_GROUP_PRESETS[0].category == CONF_OVERHEAD_LIGHTS


def test_get_light_group_preset_returns_category_match() -> None:
    """Preset lookup should resolve built-in category metadata."""
    preset = get_light_group_preset(CONF_OVERHEAD_LIGHTS)
    assert preset is not None
    assert preset.category == CONF_OVERHEAD_LIGHTS


def test_get_light_group_preset_returns_none_for_unknown_category() -> None:
    """Preset lookup should return None for custom/unknown categories."""
    assert get_light_group_preset("custom_task_scene") is None
