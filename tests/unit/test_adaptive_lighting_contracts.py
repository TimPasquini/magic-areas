"""Tests for pure Adaptive Lighting coordination contracts."""

from __future__ import annotations

from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchCandidate,
    adaptive_lighting_switch_entity_ids,
    switch_set_from_discovery_candidates,
    switch_set_from_explicit_refs,
    switch_set_from_name_candidates,
)


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
