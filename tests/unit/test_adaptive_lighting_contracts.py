"""Tests for pure Adaptive Lighting coordination contracts."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID

from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    ADAPTIVE_LIGHTING_DOMAIN,
    ATTR_LIGHTS,
    MAIN_SWITCH,
    SERVICE_SET_MANUAL_CONTROL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SLEEP_SWITCH,
    AdaptiveLightingCoordinationReason,
    AdaptiveLightingSwitchCandidate,
    AdaptiveLightingSwitchSet,
    adaptive_lighting_accent_adaptation_intents,
    adaptive_lighting_apply_data,
    adaptive_lighting_change_switch_settings_data,
    adaptive_lighting_manual_control_data,
    adaptive_lighting_manual_restore_intents,
    adaptive_lighting_sleep_switch_intents,
    adaptive_lighting_switch_entity_ids,
    switch_set_from_discovery_candidates,
    switch_set_from_explicit_refs,
    switch_set_from_name_candidates,
)

SWITCH_DOMAIN = "switch"


def _switch_set() -> AdaptiveLightingSwitchSet:
    """Build a complete AL switch set for service-contract tests."""
    switch_set = switch_set_from_explicit_refs(
        area_id="kitchen",
        switch_refs=adaptive_lighting_switch_entity_ids("Kitchen"),
    )
    assert switch_set is not None
    return switch_set


def test_adaptive_lighting_switch_entity_ids_follow_documented_convention() -> None:
    """Configuration names should map to the documented switch naming pattern."""
    assert adaptive_lighting_switch_entity_ids("Living Room") == {
        MAIN_SWITCH: "switch.adaptive_lighting_living_room",
        SLEEP_SWITCH: "switch.adaptive_lighting_sleep_mode_living_room",
        ADAPT_BRIGHTNESS_SWITCH: (
            "switch.adaptive_lighting_adapt_brightness_living_room"
        ),
        ADAPT_COLOR_SWITCH: "switch.adaptive_lighting_adapt_color_living_room",
    }


def test_switch_set_from_explicit_refs_requires_complete_switch_set() -> None:
    """Explicit references should only resolve when all four switches are present."""
    switch_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    switch_set = switch_set_from_explicit_refs(
        area_id="kitchen",
        role="overhead_lights",
        switch_refs=switch_refs,
    )

    assert switch_set is not None
    assert switch_set.area_id == "kitchen"
    assert switch_set.role == "overhead_lights"
    assert switch_set.entity_ids == (
        "switch.adaptive_lighting_kitchen",
        "switch.adaptive_lighting_sleep_mode_kitchen",
        "switch.adaptive_lighting_adapt_brightness_kitchen",
        "switch.adaptive_lighting_adapt_color_kitchen",
    )

    incomplete_refs = dict(switch_refs)
    incomplete_refs.pop(ADAPT_COLOR_SWITCH)
    assert (
        switch_set_from_explicit_refs(
            area_id="kitchen",
            switch_refs=incomplete_refs,
        )
        is None
    )


def test_switch_set_from_explicit_refs_rejects_non_switch_entities() -> None:
    """Adaptive Lighting switch refs must point at switch entities."""
    switch_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    switch_refs[MAIN_SWITCH] = "light.not_a_switch"

    assert (
        switch_set_from_explicit_refs(area_id="kitchen", switch_refs=switch_refs)
        is None
    )


def test_switch_set_from_name_candidates_requires_all_four_conventional_ids() -> None:
    """Name matching should resolve only when all expected switch IDs are candidates."""
    expected = adaptive_lighting_switch_entity_ids("Bedroom")
    switch_set = switch_set_from_name_candidates(
        area_id="bedroom",
        name="Bedroom",
        role="sleep_lights",
        candidate_entity_ids=(
            "switch.unrelated",
            *expected.values(),
        ),
    )

    assert switch_set is not None
    assert switch_set.role == "sleep_lights"
    assert switch_set.entity_ids == (
        "switch.adaptive_lighting_bedroom",
        "switch.adaptive_lighting_sleep_mode_bedroom",
        "switch.adaptive_lighting_adapt_brightness_bedroom",
        "switch.adaptive_lighting_adapt_color_bedroom",
    )

    assert (
        switch_set_from_name_candidates(
            area_id="bedroom",
            name="Bedroom",
            candidate_entity_ids=(
                expected[MAIN_SWITCH],
                expected[SLEEP_SWITCH],
                expected[ADAPT_BRIGHTNESS_SWITCH],
            ),
        )
        is None
    )


def test_discovery_candidates_resolve_one_complete_area_switch_set() -> None:
    """Area discovery should resolve only a complete four-switch AL set."""
    kitchen_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    bedroom_refs = adaptive_lighting_switch_entity_ids("Bedroom")

    switch_set = switch_set_from_discovery_candidates(
        area_id="kitchen",
        role="overhead_lights",
        candidates=(
            *(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="kitchen")
                for entity_id in kitchen_refs.values()
            ),
            *(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="bedroom")
                for entity_id in bedroom_refs.values()
            ),
        ),
    )

    assert switch_set is not None
    assert switch_set.area_id == "kitchen"
    assert switch_set.role == "overhead_lights"
    assert switch_set.entity_ids == tuple(kitchen_refs.values())


def test_discovery_candidates_require_one_unambiguous_complete_set() -> None:
    """Ambiguous or incomplete discovery must not silently pick a switch set."""
    kitchen_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    dining_refs = adaptive_lighting_switch_entity_ids("Dining")

    assert (
        switch_set_from_discovery_candidates(
            area_id="kitchen",
            candidates=(
                *(
                    AdaptiveLightingSwitchCandidate(
                        entity_id=entity_id,
                        area_id="kitchen",
                    )
                    for entity_id in kitchen_refs.values()
                ),
                *(
                    AdaptiveLightingSwitchCandidate(
                        entity_id=entity_id,
                        area_id="kitchen",
                    )
                    for entity_id in dining_refs.values()
                ),
            ),
        )
        is None
    )

    incomplete_refs = dict(kitchen_refs)
    incomplete_refs.pop(ADAPT_COLOR_SWITCH)
    assert (
        switch_set_from_discovery_candidates(
            area_id="kitchen",
            candidates=(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="kitchen")
                for entity_id in incomplete_refs.values()
            ),
        )
        is None
    )


def test_discovery_candidates_do_not_match_area_less_switches_by_name_only() -> None:
    """Automatic discovery should not adopt unscoped AL switches by naming alone."""
    kitchen_refs = adaptive_lighting_switch_entity_ids("Kitchen")

    assert (
        switch_set_from_discovery_candidates(
            area_id="kitchen",
            candidates=(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id)
                for entity_id in kitchen_refs.values()
            ),
        )
        is None
    )


def test_discovery_candidates_can_require_labels() -> None:
    """Label matching should narrow discovery before completeness is evaluated."""
    kitchen_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    label_ids = frozenset({"ma_living_room", "ma_overhead"})
    label_names = frozenset({"ma:living-room", "ma:overhead"})

    switch_set = switch_set_from_discovery_candidates(
        area_id="kitchen",
        role="overhead_lights",
        required_label_ids=("ma_living_room",),
        required_label_names=("ma:overhead",),
        candidates=(
            AdaptiveLightingSwitchCandidate(
                entity_id=entity_id,
                area_id="kitchen",
                label_ids=label_ids,
                label_names=label_names,
            )
            for entity_id in kitchen_refs.values()
        ),
    )

    assert switch_set is not None
    assert switch_set.entity_ids == tuple(kitchen_refs.values())

    assert (
        switch_set_from_discovery_candidates(
            area_id="kitchen",
            required_label_ids=("ma_missing",),
            candidates=(
                AdaptiveLightingSwitchCandidate(
                    entity_id=entity_id,
                    area_id="kitchen",
                    label_ids=label_ids,
                )
                for entity_id in kitchen_refs.values()
            ),
        )
        is None
    )


def test_adaptive_lighting_apply_data_uses_documented_service_shape() -> None:
    """Apply service data should use entity_id for AL switch and lights for targets."""
    switch_set = _switch_set()

    data = adaptive_lighting_apply_data(
        switch_set,
        light_entity_ids=("light.lamp",),
        adapt_brightness=True,
        adapt_color=False,
        turn_on_lights=False,
        transition=1.5,
    )

    assert data == {
        ATTR_ENTITY_ID: "switch.adaptive_lighting_kitchen",
        ATTR_LIGHTS: ("light.lamp",),
        "adapt_brightness": True,
        "adapt_color": False,
        "turn_on_lights": False,
        "transition": 1.5,
    }


def test_adaptive_lighting_manual_control_data_uses_documented_service_shape() -> None:
    """Manual-control service data should target the AL switch and selected lights."""
    switch_set = _switch_set()

    data = adaptive_lighting_manual_control_data(
        switch_set,
        light_entity_ids=("light.lamp",),
        manual_control=False,
    )

    assert data == {
        ATTR_ENTITY_ID: "switch.adaptive_lighting_kitchen",
        ATTR_LIGHTS: ("light.lamp",),
        "manual_control": False,
    }


def test_adaptive_lighting_change_switch_settings_data_targets_behavior_switch() -> (
    None
):
    """Switch-setting service data should target the behavior switch being changed."""
    data = adaptive_lighting_change_switch_settings_data(
        "switch.adaptive_lighting_adapt_brightness_kitchen",
        adapt_brightness=False,
        use_defaults="current",
    )

    assert data == {
        ATTR_ENTITY_ID: "switch.adaptive_lighting_adapt_brightness_kitchen",
        "adapt_brightness": False,
        "use_defaults": "current",
    }


def test_sleep_switch_intent_tracks_magic_areas_sleep_state() -> None:
    """MA sleep state should map to the Adaptive Lighting sleep switch."""
    switch_set = _switch_set()

    active_intent = adaptive_lighting_sleep_switch_intents(
        switch_set,
        sleep_active=True,
    )[0]

    assert active_intent.domain == SWITCH_DOMAIN
    assert active_intent.service == SERVICE_TURN_ON
    assert active_intent.data == {
        ATTR_ENTITY_ID: "switch.adaptive_lighting_sleep_mode_kitchen"
    }
    assert active_intent.reason is AdaptiveLightingCoordinationReason.SLEEP_ACTIVE

    cleared_intent = adaptive_lighting_sleep_switch_intents(
        switch_set,
        sleep_active=False,
    )[0]
    assert cleared_intent.service == SERVICE_TURN_OFF
    assert cleared_intent.reason is AdaptiveLightingCoordinationReason.SLEEP_CLEARED


def test_accent_adaptation_intents_pause_and_restore_behavior_switches() -> None:
    """MA accent state should pause, then restore, brightness/color adaptation."""
    switch_set = _switch_set()

    pause_intents = adaptive_lighting_accent_adaptation_intents(
        switch_set,
        accent_active=True,
    )

    assert tuple(intent.domain for intent in pause_intents) == (
        SWITCH_DOMAIN,
        SWITCH_DOMAIN,
    )
    assert tuple(intent.service for intent in pause_intents) == (
        SERVICE_TURN_OFF,
        SERVICE_TURN_OFF,
    )
    assert tuple(intent.data[ATTR_ENTITY_ID] for intent in pause_intents) == (
        "switch.adaptive_lighting_adapt_brightness_kitchen",
        "switch.adaptive_lighting_adapt_color_kitchen",
    )
    assert {intent.reason for intent in pause_intents} == {
        AdaptiveLightingCoordinationReason.ACCENT_ACTIVE
    }

    restore_intents = adaptive_lighting_accent_adaptation_intents(
        switch_set,
        accent_active=False,
    )
    assert tuple(intent.service for intent in restore_intents) == (
        SERVICE_TURN_ON,
        SERVICE_TURN_ON,
    )
    assert {intent.reason for intent in restore_intents} == {
        AdaptiveLightingCoordinationReason.ACCENT_CLEARED
    }


def test_manual_restore_intent_waits_for_magic_areas_cooldown() -> None:
    """MA should clear AL manual control only after its own cooldown expires."""
    switch_set = _switch_set()

    assert (
        adaptive_lighting_manual_restore_intents(
            switch_set,
            light_entity_ids=("light.lamp",),
            cooldown_expired=False,
        )
        == ()
    )

    intents = adaptive_lighting_manual_restore_intents(
        switch_set,
        light_entity_ids=("light.lamp",),
        cooldown_expired=True,
    )

    assert len(intents) == 1
    assert intents[0].domain == ADAPTIVE_LIGHTING_DOMAIN
    assert intents[0].service == SERVICE_SET_MANUAL_CONTROL
    assert intents[0].data == {
        ATTR_ENTITY_ID: "switch.adaptive_lighting_kitchen",
        ATTR_LIGHTS: ("light.lamp",),
        "manual_control": False,
    }
    assert (
        intents[0].reason
        is AdaptiveLightingCoordinationReason.MANUAL_OVERRIDE_COOLDOWN_EXPIRED
    )
