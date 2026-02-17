"""Tests for light scene/category configuration resolution."""


from custom_components.magic_areas.core.light_control import (
    resolve_light_category_config,
)


# Mock config keys and mappings (simulate light_groups.py)
MOCK_OVERHEAD_LIGHTS = "overhead_lights"
MOCK_OVERHEAD_LIGHTS_STATES = "overhead_lights_states"
MOCK_OVERHEAD_LIGHTS_ACT_ON = "overhead_lights_act_on"

MOCK_SLEEP_LIGHTS = "sleep_lights"
MOCK_SLEEP_LIGHTS_STATES = "sleep_lights_states"
MOCK_SLEEP_LIGHTS_ACT_ON = "sleep_lights_act_on"

MOCK_ACCENT_LIGHTS = "accent_lights"
MOCK_ACCENT_LIGHTS_STATES = "accent_lights_states"
MOCK_ACCENT_LIGHTS_ACT_ON = "accent_lights_act_on"

MOCK_TASK_LIGHTS = "task_lights"
MOCK_TASK_LIGHTS_STATES = "task_lights_states"
MOCK_TASK_LIGHTS_ACT_ON = "task_lights_act_on"

MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY = "occupancy"
MOCK_LIGHT_GROUP_ACT_ON_STATE = "state"
MOCK_DEFAULT_LIGHT_GROUP_ACT_ON = [
    MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY,
    MOCK_LIGHT_GROUP_ACT_ON_STATE,
]

MOCK_LIGHT_GROUP_STATES = {
    MOCK_OVERHEAD_LIGHTS: MOCK_OVERHEAD_LIGHTS_STATES,
    MOCK_SLEEP_LIGHTS: MOCK_SLEEP_LIGHTS_STATES,
    MOCK_ACCENT_LIGHTS: MOCK_ACCENT_LIGHTS_STATES,
    MOCK_TASK_LIGHTS: MOCK_TASK_LIGHTS_STATES,
}

MOCK_LIGHT_GROUP_ACT_ON = {
    MOCK_OVERHEAD_LIGHTS: MOCK_OVERHEAD_LIGHTS_ACT_ON,
    MOCK_SLEEP_LIGHTS: MOCK_SLEEP_LIGHTS_ACT_ON,
    MOCK_ACCENT_LIGHTS: MOCK_ACCENT_LIGHTS_ACT_ON,
    MOCK_TASK_LIGHTS: MOCK_TASK_LIGHTS_ACT_ON,
}


class TestResolveLightCategoryConfig:
    """Tests for resolve_light_category_config function."""

    def test_empty_feature_config(self) -> None:
        """Test with empty feature config uses defaults."""
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config={},
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == []
        assert act_on == MOCK_DEFAULT_LIGHT_GROUP_ACT_ON

    def test_overhead_lights_config(self) -> None:
        """Test resolving overhead lights configuration."""
        feature_config = {
            MOCK_OVERHEAD_LIGHTS_STATES: ["occupied", "bright"],
            MOCK_OVERHEAD_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == ["occupied", "bright"]
        assert act_on == [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY]

    def test_sleep_lights_config(self) -> None:
        """Test resolving sleep lights configuration."""
        feature_config = {
            MOCK_SLEEP_LIGHTS_STATES: ["sleep", "dark"],
            MOCK_SLEEP_LIGHTS_ACT_ON: [
                MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY,
                MOCK_LIGHT_GROUP_ACT_ON_STATE,
            ],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_SLEEP_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == ["sleep", "dark"]
        assert act_on == [
            MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY,
            MOCK_LIGHT_GROUP_ACT_ON_STATE,
        ]

    def test_accent_lights_config(self) -> None:
        """Test resolving accent lights configuration."""
        feature_config = {
            MOCK_ACCENT_LIGHTS_STATES: ["extended"],
            MOCK_ACCENT_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_STATE],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_ACCENT_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == ["extended"]
        assert act_on == [MOCK_LIGHT_GROUP_ACT_ON_STATE]

    def test_task_lights_config(self) -> None:
        """Test resolving task lights configuration."""
        feature_config = {
            MOCK_TASK_LIGHTS_STATES: ["occupied"],
            MOCK_TASK_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_TASK_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == ["occupied"]
        assert act_on == [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY]

    def test_unknown_category(self) -> None:
        """Test with unknown category returns defaults."""
        assigned_states, act_on = resolve_light_category_config(
            category="unknown_lights",
            feature_config={
                "unknown_lights_states": ["occupied"],
                "unknown_lights_act_on": [MOCK_LIGHT_GROUP_ACT_ON_STATE],
            },
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == []
        assert act_on == MOCK_DEFAULT_LIGHT_GROUP_ACT_ON

    def test_partial_config(self) -> None:
        """Test with only states config, act_on uses default."""
        feature_config = {
            MOCK_OVERHEAD_LIGHTS_STATES: ["occupied"],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == ["occupied"]
        assert act_on == MOCK_DEFAULT_LIGHT_GROUP_ACT_ON

    def test_all_light_categories(self) -> None:
        """Test resolving config for all light categories."""
        feature_config = {
            MOCK_OVERHEAD_LIGHTS_STATES: ["occupied", "bright"],
            MOCK_OVERHEAD_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY],
            MOCK_SLEEP_LIGHTS_STATES: ["sleep", "dark"],
            MOCK_SLEEP_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_STATE],
            MOCK_ACCENT_LIGHTS_STATES: ["extended"],
            MOCK_ACCENT_LIGHTS_ACT_ON: [
                MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY,
                MOCK_LIGHT_GROUP_ACT_ON_STATE,
            ],
            MOCK_TASK_LIGHTS_STATES: ["occupied"],
            MOCK_TASK_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY],
        }

        # Test overhead
        overhead_states, overhead_act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert overhead_states == ["occupied", "bright"]
        assert overhead_act_on == [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY]

        # Test sleep
        sleep_states, sleep_act_on = resolve_light_category_config(
            category=MOCK_SLEEP_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert sleep_states == ["sleep", "dark"]
        assert sleep_act_on == [MOCK_LIGHT_GROUP_ACT_ON_STATE]

        # Test accent
        accent_states, accent_act_on = resolve_light_category_config(
            category=MOCK_ACCENT_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert accent_states == ["extended"]
        assert accent_act_on == [
            MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY,
            MOCK_LIGHT_GROUP_ACT_ON_STATE,
        ]

        # Test task
        task_states, task_act_on = resolve_light_category_config(
            category=MOCK_TASK_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert task_states == ["occupied"]
        assert task_act_on == [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY]

    def test_empty_states_list(self) -> None:
        """Test with explicitly empty states list."""
        feature_config = {
            MOCK_OVERHEAD_LIGHTS_STATES: [],
            MOCK_OVERHEAD_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_STATE],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert assigned_states == []
        assert act_on == [MOCK_LIGHT_GROUP_ACT_ON_STATE]

    def test_return_type_is_list(self) -> None:
        """Test that returned values are lists, not sequences."""
        feature_config = {
            MOCK_OVERHEAD_LIGHTS_STATES: ["occupied"],
            MOCK_OVERHEAD_LIGHTS_ACT_ON: [MOCK_LIGHT_GROUP_ACT_ON_OCCUPANCY],
        }
        assigned_states, act_on = resolve_light_category_config(
            category=MOCK_OVERHEAD_LIGHTS,
            feature_config=feature_config,
            light_group_states_map=MOCK_LIGHT_GROUP_STATES,
            light_group_act_on_map=MOCK_LIGHT_GROUP_ACT_ON,
            default_act_on=MOCK_DEFAULT_LIGHT_GROUP_ACT_ON,
        )
        assert isinstance(assigned_states, list)
        assert isinstance(act_on, list)
