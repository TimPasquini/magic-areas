"""Tests for light-group preset declarations and schema defaults."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
)
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    LIGHT_GROUP_FEATURE_SCHEMA,
    LIGHT_GROUP_PRESETS,
    adaptive_lighting_switch_set,
    adaptive_lighting_diagnostics,
    adaptive_lighting_manage_all_lights,
    adaptive_lighting_manages_role,
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
    assert defaults[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE] == "ignore"
    assert defaults[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is False
    assert defaults[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS] == {}


def test_adaptive_lighting_manage_all_lights_reads_explicit_config_only() -> None:
    """Room-level AL management should come only from its explicit gate."""
    assert adaptive_lighting_manage_all_lights({}) is False
    assert (
        adaptive_lighting_manage_all_lights(
            {"adaptive_lighting_managed_roles": ["all_lights"]}
        )
        is False
    )
    assert (
        adaptive_lighting_manage_all_lights(
            {
                "adaptive_lighting_manage_all_lights": True,
                "adaptive_lighting_managed_roles": ["all_lights"],
            }
        )
        is True
    )


def test_adaptive_lighting_manages_role_separates_room_and_role_gates() -> None:
    """Room-level and role-level managed AL gates should not imply each other."""
    feature_config = {
        "adaptive_lighting_manage_all_lights": True,
        "adaptive_lighting_managed_roles": [CONF_OVERHEAD_LIGHTS],
    }

    assert adaptive_lighting_manages_role(feature_config, "all_lights") is True
    assert adaptive_lighting_manages_role(feature_config, CONF_OVERHEAD_LIGHTS) is True
    assert adaptive_lighting_manages_role(feature_config, "task_lights") is False


def test_get_light_group_preset_returns_category_match() -> None:
    """Preset lookup should resolve built-in category metadata."""
    preset = get_light_group_preset(CONF_OVERHEAD_LIGHTS)
    assert preset is not None
    assert preset.category == CONF_OVERHEAD_LIGHTS


def test_get_light_group_preset_returns_none_for_unknown_category() -> None:
    """Preset lookup should return None for custom/unknown categories."""
    assert get_light_group_preset("custom_task_scene") is None


def test_adaptive_lighting_switch_set_reads_role_scoped_explicit_refs() -> None:
    """Explicit AL adoption should attach only to the configured light role."""
    feature_config: dict[str, object] = {
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
        ),
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
            CONF_OVERHEAD_LIGHTS: {
                MAIN_SWITCH: "switch.adaptive_lighting_kitchen_overhead",
                SLEEP_SWITCH: "switch.adaptive_lighting_sleep_mode_kitchen_overhead",
                ADAPT_BRIGHTNESS_SWITCH: (
                    "switch.adaptive_lighting_adapt_brightness_kitchen_overhead"
                ),
                ADAPT_COLOR_SWITCH: (
                    "switch.adaptive_lighting_adapt_color_kitchen_overhead"
                ),
            }
        },
    }

    switch_set = adaptive_lighting_switch_set(
        feature_config,
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    )

    assert switch_set is not None
    assert switch_set.area_id == "kitchen"
    assert switch_set.role == CONF_OVERHEAD_LIGHTS
    assert (
        adaptive_lighting_switch_set(
            feature_config,
            area_id="kitchen",
            category="sleep_lights",
        )
        is None
    )


def test_adaptive_lighting_switch_set_fails_closed_for_incomplete_refs() -> None:
    """Incomplete AL switch config should not partially enable coordination."""
    switch_set = adaptive_lighting_switch_set(
        {
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: {
                    MAIN_SWITCH: "switch.adaptive_lighting_kitchen_overhead",
                }
            },
        },
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    )

    assert switch_set is None


def test_adaptive_lighting_switch_set_is_inert_in_ignore_mode() -> None:
    """Stale AL switch refs should not enable coordination unless adoption is active."""
    switch_set = adaptive_lighting_switch_set(
        {
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: {
                    MAIN_SWITCH: "switch.adaptive_lighting_kitchen_overhead",
                    SLEEP_SWITCH: "switch.adaptive_lighting_sleep_mode_kitchen_overhead",
                    ADAPT_BRIGHTNESS_SWITCH: (
                        "switch.adaptive_lighting_adapt_brightness_kitchen_overhead"
                    ),
                    ADAPT_COLOR_SWITCH: (
                        "switch.adaptive_lighting_adapt_color_kitchen_overhead"
                    ),
                }
            },
        },
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    )

    assert switch_set is None


def test_adaptive_lighting_diagnostics_explain_inactive_modes() -> None:
    """AL diagnostics should explain why coordination is inactive."""
    assert adaptive_lighting_diagnostics(
        {CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE},
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    ) == {
        "mode": LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
        "role": CONF_OVERHEAD_LIGHTS,
        "active": False,
        "reason": "mode_ignore",
    }

    assert adaptive_lighting_diagnostics(
        {
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: {MAIN_SWITCH: "switch.adaptive_lighting_kitchen"}
            },
        },
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    )["reason"] == "incomplete_switch_set"


def test_adaptive_lighting_diagnostics_explain_active_adopted_switch_set() -> None:
    """AL diagnostics should expose the associated switch set when active."""
    diagnostics = adaptive_lighting_diagnostics(
        {
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: {
                    MAIN_SWITCH: "switch.adaptive_lighting_kitchen_overhead",
                    SLEEP_SWITCH: "switch.adaptive_lighting_sleep_mode_kitchen_overhead",
                    ADAPT_BRIGHTNESS_SWITCH: (
                        "switch.adaptive_lighting_adapt_brightness_kitchen_overhead"
                    ),
                    ADAPT_COLOR_SWITCH: (
                        "switch.adaptive_lighting_adapt_color_kitchen_overhead"
                    ),
                }
            },
        },
        area_id="kitchen",
        category=CONF_OVERHEAD_LIGHTS,
    )

    assert diagnostics == {
        "mode": LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
        "role": CONF_OVERHEAD_LIGHTS,
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": "switch.adaptive_lighting_kitchen_overhead",
    }


def test_adaptive_lighting_diagnostics_explain_active_managed_all_lights() -> None:
    """AL diagnostics should treat room-level managed AL as explicitly gated."""
    diagnostics = adaptive_lighting_diagnostics(
        {
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: "manage",
            "adaptive_lighting_manage_all_lights": True,
            "adaptive_lighting_managed_roles": [],
        },
        area_id="kitchen",
        area_name="Kitchen",
        category="all_lights",
        light_entity_ids=["light.one"],
    )

    assert diagnostics == {
        "mode": "manage",
        "role": "all_lights",
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": (
            "switch.adaptive_lighting_magic_areas_kitchen_all_lights"
        ),
    }
