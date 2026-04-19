"""Unit tests for core/climate_control.py."""


from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.policies.climate import (
    ClimatePresetPolicy,
    build_preset_policy,
)


class TestClimatePresetPolicy:
    """Tests for ClimatePresetPolicy."""

    def test_select_preset_for_clear_state(self) -> None:
        """Should return CLEAR preset when CLEAR state added."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.CLEAR: "away",
                AreaStates.OCCUPIED: "home",
            }
        )
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.CLEAR],
            current_states=[AreaStates.CLEAR],
        )
        assert preset == "away"

    def test_select_preset_by_priority(self) -> None:
        """Should select highest priority state with configured preset."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.OCCUPIED: "home",
                AreaStates.SLEEP: "sleep",
                AreaStates.EXTENDED: "eco",
            }
        )
        # SLEEP has higher priority than OCCUPIED
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.SLEEP, AreaStates.OCCUPIED],
            current_states=[AreaStates.SLEEP, AreaStates.OCCUPIED],
        )
        assert preset == "sleep"

    def test_returns_none_when_no_preset_configured(self) -> None:
        """Should return None when state has no preset mapping."""
        policy = ClimatePresetPolicy(preset_map={AreaStates.OCCUPIED: "home"})
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.DARK],
            current_states=[AreaStates.DARK],
        )
        assert preset is None

    def test_clear_takes_precedence(self) -> None:
        """Should return CLEAR preset even when other states present."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.CLEAR: "away",
                AreaStates.SLEEP: "sleep",
                AreaStates.OCCUPIED: "home",
            }
        )
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.CLEAR, AreaStates.SLEEP],
            current_states=[AreaStates.CLEAR, AreaStates.SLEEP, AreaStates.OCCUPIED],
        )
        assert preset == "away"

    def test_uses_custom_priority_order(self) -> None:
        """Should respect custom priority order."""
        # Reverse priority: OCCUPIED before SLEEP
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.OCCUPIED: "home",
                AreaStates.SLEEP: "sleep",
            },
            priority_order=[AreaStates.OCCUPIED, AreaStates.SLEEP],
        )
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.SLEEP, AreaStates.OCCUPIED],
            current_states=[AreaStates.SLEEP, AreaStates.OCCUPIED],
        )
        assert preset == "home"  # OCCUPIED wins with custom order

    def test_only_considers_new_states(self) -> None:
        """Should only look at new_states, not all current_states."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.OCCUPIED: "home",
                AreaStates.SLEEP: "sleep",
            }
        )
        # SLEEP is current but not new, OCCUPIED is new
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.SLEEP, AreaStates.OCCUPIED],
        )
        assert preset == "home"

    def test_empty_new_states(self) -> None:
        """Should return None when no new states."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.OCCUPIED: "home",
            }
        )
        preset = policy.select_preset_for_state_change(
            new_states=[],
            current_states=[AreaStates.OCCUPIED],
        )
        assert preset is None

    def test_extended_state_priority(self) -> None:
        """Should select EXTENDED when EXTENDED and OCCUPIED both new."""
        policy = ClimatePresetPolicy(
            preset_map={
                AreaStates.OCCUPIED: "home",
                AreaStates.EXTENDED: "eco",
            }
        )
        preset = policy.select_preset_for_state_change(
            new_states=[AreaStates.EXTENDED, AreaStates.OCCUPIED],
            current_states=[AreaStates.EXTENDED, AreaStates.OCCUPIED],
        )
        assert preset == "eco"  # EXTENDED has higher priority


class TestBuildPresetPolicy:
    """Tests for build_preset_policy()."""

    def test_builds_policy_from_config(self) -> None:
        """Should build policy with presets from config."""
        config = {
            "preset_occupied": "home",
            "preset_sleep": "sleep",
            "preset_clear": "away",
            "preset_extended": "eco",
        }
        policy = build_preset_policy(config)
        assert policy.preset_map[AreaStates.OCCUPIED] == "home"
        assert policy.preset_map[AreaStates.SLEEP] == "sleep"
        assert policy.preset_map[AreaStates.CLEAR] == "away"
        assert policy.preset_map[AreaStates.EXTENDED] == "eco"

    def test_uses_defaults_when_missing(self) -> None:
        """Should use default values when config keys missing."""
        config: dict[str, object] = {}
        policy = build_preset_policy(config)
        # Should have all states with default values
        assert AreaStates.OCCUPIED in policy.preset_map
        assert AreaStates.SLEEP in policy.preset_map
        assert AreaStates.CLEAR in policy.preset_map
        assert AreaStates.EXTENDED in policy.preset_map

    def test_partial_config(self) -> None:
        """Should use defaults for missing keys."""
        config = {
            "preset_occupied": "custom_home",
        }
        policy = build_preset_policy(config)
        assert policy.preset_map[AreaStates.OCCUPIED] == "custom_home"
        # Others should have defaults
        assert AreaStates.SLEEP in policy.preset_map
        assert AreaStates.CLEAR in policy.preset_map
