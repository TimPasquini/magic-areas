"""Parity tests for climate preset -> control-group conversion."""

from custom_components.magic_areas.core.controls.policies.climate import (
    climate_preset_to_control_group,
)
from custom_components.magic_areas.core.controls import ControlActionType


def test_preset_maps_to_activate_action() -> None:
    """Selected preset should produce climate preset action."""
    decision = climate_preset_to_control_group("climate.living_room", "sleep")

    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].service == "set_preset_mode"
    assert decision.actions[0].service_data["preset_mode"] == "sleep"


def test_missing_preset_or_entity_is_noop() -> None:
    """Missing inputs should produce NOOP decisions."""
    no_entity = climate_preset_to_control_group(None, "sleep")
    no_preset = climate_preset_to_control_group("climate.living_room", None)

    assert no_entity.action_type == ControlActionType.NOOP
    assert no_preset.action_type == ControlActionType.NOOP
