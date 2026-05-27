"""Unit tests for cover automation policy."""

from homeassistant.const import SERVICE_CLOSE_COVER, SERVICE_OPEN_COVER, STATE_CLOSED

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import ControlActionType
from custom_components.magic_areas.core.controls.policies.cover import (
    CoverGroupsConfig,
    CoverPresetAction,
    CoverPresetConfig,
    CoverPresetRole,
    cover_preset_decision_to_control_group,
    evaluate_cover_presets,
)
from custom_components.magic_areas.switch.cover_control import CoverControlSwitch


class _State:
    """Minimal state object for manual-hold tests."""

    def __init__(self, state: str) -> None:
        self.state = state


class _Event:
    """Minimal event object for manual-hold tests."""

    def __init__(self, entity_id: str, old_state: str, new_state: str) -> None:
        self.data = {
            "entity_id": entity_id,
            "old_state": _State(old_state),
            "new_state": _State(new_state),
        }


def _config() -> CoverGroupsConfig:
    """Return a representative cover automation config."""
    return CoverGroupsConfig(
        automation_device_classes=("blind", "shade"),
        manual_hold_seconds=900,
        presets=(
            CoverPresetConfig(
                role=CoverPresetRole.DAYLIGHT,
                action=CoverPresetAction.OPEN,
                states=(AreaStates.OCCUPIED.value,),
            ),
            CoverPresetConfig(
                role=CoverPresetRole.PRIVACY,
                action=CoverPresetAction.CLOSE,
                states=(AreaStates.SLEEP.value,),
            ),
            CoverPresetConfig(
                role=CoverPresetRole.ACCENT,
                action=CoverPresetAction.CLOSE,
                states=(AreaStates.ACCENT.value,),
            ),
        ),
    )


def test_cover_policy_opens_for_daylight_state() -> None:
    """Daylight preset should open covers when its states match."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value,),
    )

    assert decision.action is CoverPresetAction.OPEN
    assert decision.role is CoverPresetRole.DAYLIGHT


def test_cover_policy_privacy_blocks_daylight() -> None:
    """Privacy/Sleep should win over daylight when both states are present."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value, AreaStates.SLEEP.value),
    )

    assert decision.action is CoverPresetAction.CLOSE
    assert decision.role is CoverPresetRole.PRIVACY


def test_cover_policy_accent_blocks_daylight() -> None:
    """Media/Accent should win over daylight while active."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value, AreaStates.ACCENT.value),
    )

    assert decision.action is CoverPresetAction.CLOSE
    assert decision.role is CoverPresetRole.ACCENT


def test_cover_policy_accent_release_restores_daylight() -> None:
    """When accent clears, daylight can apply again if its state still matches."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value,),
    )

    assert decision.action is CoverPresetAction.OPEN
    assert decision.role is CoverPresetRole.DAYLIGHT


def test_cover_policy_manual_hold_blocks_action() -> None:
    """Manual hold should prevent immediate reversal."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value,),
        manual_hold_active=True,
    )

    assert decision.action is CoverPresetAction.NONE
    assert decision.reason == "manual_hold_active"


def test_cover_decision_targets_cover_helpers_only() -> None:
    """Cover policy should emit cover service calls, not cross-domain light actions."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.OCCUPIED.value,),
    )
    control_decision = cover_preset_decision_to_control_group(
        decision=decision,
        cover_group_entity_ids={
            "blind": "cover.kitchen_blinds",
            "shade": "cover.kitchen_shades",
        },
        cover_group_states={
            "cover.kitchen_blinds": STATE_CLOSED,
            "cover.kitchen_shades": STATE_CLOSED,
        },
    )

    assert control_decision.action_type is ControlActionType.ACTIVATE
    assert control_decision.actions[0].domain == "cover"
    assert control_decision.actions[0].service == SERVICE_OPEN_COVER
    assert control_decision.actions[0].target_entity_ids == (
        "cover.kitchen_blinds",
        "cover.kitchen_shades",
    )


def test_cover_decision_closes_for_privacy() -> None:
    """Close decisions should use the close-cover service."""
    decision = evaluate_cover_presets(
        _config(),
        current_states=(AreaStates.SLEEP.value,),
    )
    control_decision = cover_preset_decision_to_control_group(
        decision=decision,
        cover_group_entity_ids={"blind": "cover.kitchen_blinds"},
        cover_group_states={"cover.kitchen_blinds": "open"},
    )

    assert control_decision.actions[0].service == SERVICE_CLOSE_COVER


async def test_cover_switch_manual_state_change_starts_hold() -> None:
    """Unexpected cover group movement should start a manual hold."""
    switch = object.__new__(CoverControlSwitch)
    switch._manual_hold_seconds = 900
    switch._manual_hold_until_monotonic = 0.0
    switch._expected_cover_group_state_changes = set()

    await switch.cover_group_state_changed(
        _Event("cover.kitchen_blinds", "open", "closed")  # type: ignore[arg-type]
    )

    assert switch._manual_hold_active()


async def test_cover_switch_expected_state_change_does_not_start_hold() -> None:
    """Magic Areas cover commands should not be treated as manual movement."""
    switch = object.__new__(CoverControlSwitch)
    switch._manual_hold_seconds = 900
    switch._manual_hold_until_monotonic = 0.0
    switch._expected_cover_group_state_changes = {"cover.kitchen_blinds"}

    await switch.cover_group_state_changed(
        _Event("cover.kitchen_blinds", "open", "closed")  # type: ignore[arg-type]
    )

    assert not switch._manual_hold_active()
    assert switch._expected_cover_group_state_changes == set()
