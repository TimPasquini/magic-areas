"""Tests for pure Adaptive Lighting coordination contracts."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID

from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    ADAPTIVE_LIGHTING_DOMAIN,
    ATTR_LIGHTS,
    MAIN_SWITCH,
    MANAGED_ADAPTIVE_LIGHTING_AREA_ID,
    MANAGED_ADAPTIVE_LIGHTING_OWNED_DATA_KEYS,
    MANAGED_ADAPTIVE_LIGHTING_OWNED_OPTION_KEYS,
    MANAGED_ADAPTIVE_LIGHTING_ROLE,
    SERVICE_SET_MANUAL_CONTROL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SLEEP_SWITCH,
    AdaptiveLightingCoordinationReason,
    AdaptiveLightingSwitchCandidate,
    AdaptiveLightingSwitchSet,
    ExistingAdaptiveLightingConfigEntry,
    ManagedAdaptiveLightingReconcileAction,
    adaptive_lighting_accent_adaptation_intents,
    adaptive_lighting_apply_data,
    adaptive_lighting_change_switch_settings_data,
    adaptive_lighting_manual_control_data,
    adaptive_lighting_manual_restore_intents,
    adaptive_lighting_sleep_switch_intents,
    adaptive_lighting_state_coordination_intents,
    adaptive_lighting_switch_entity_ids,
    is_managed_adaptive_lighting_owned_data_key,
    is_managed_adaptive_lighting_entry,
    is_managed_adaptive_lighting_owned_option_key,
    managed_adaptive_lighting_config,
    managed_adaptive_lighting_config_name,
    managed_adaptive_lighting_options,
    managed_adaptive_lighting_reconcile_plan,
    switch_set_from_discovery_candidates,
    switch_sets_from_discovery_candidates,
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


def test_managed_adaptive_lighting_config_names_are_role_scoped() -> None:
    """MA-managed AL config names should identify both area and light role."""
    assert (
        managed_adaptive_lighting_config_name(
            area_name="Living Room",
            role="overhead_lights",
        )
        == "Magic Areas Living Room overhead"
    )
    assert (
        managed_adaptive_lighting_config_name(
            area_name="Living Room",
            role="all_lights",
        )
        == "Magic Areas Living Room all"
    )


def test_managed_adaptive_lighting_config_normalizes_membership() -> None:
    """Desired managed AL configs should carry only stable light members."""
    config = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=(
            "light.ceiling",
            "switch.not_a_light",
            "light.ceiling",
            "light.lamp",
        ),
    )

    assert config is not None
    assert config.area_id == "living_room"
    assert config.role == "overhead_lights"
    assert config.name == "Magic Areas Living Room overhead"
    assert config.data == {
        "name": "Magic Areas Living Room overhead",
        MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
        MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
    }
    assert config.light_entity_ids == ("light.ceiling", "light.lamp")
    assert config.switch_refs == adaptive_lighting_switch_entity_ids(
        "Magic Areas Living Room overhead"
    )


def test_managed_adaptive_lighting_config_requires_light_membership() -> None:
    """Manage mode should not create empty AL configs."""
    assert (
        managed_adaptive_lighting_config(
            area_id="living_room",
            area_name="Living Room",
            role="overhead_lights",
            light_entity_ids=("switch.not_a_light",),
        )
        is None
    )


def test_managed_adaptive_lighting_owned_keys_are_limited_to_membership() -> None:
    """MA should not claim ownership of AL behavior-tuning option keys."""
    assert (
        frozenset(
            {
                "name",
                MANAGED_ADAPTIVE_LIGHTING_AREA_ID,
                MANAGED_ADAPTIVE_LIGHTING_ROLE,
            }
        )
        == MANAGED_ADAPTIVE_LIGHTING_OWNED_DATA_KEYS
    )
    assert frozenset({"lights"}) == MANAGED_ADAPTIVE_LIGHTING_OWNED_OPTION_KEYS
    assert is_managed_adaptive_lighting_owned_data_key("name")
    assert is_managed_adaptive_lighting_owned_option_key("lights")

    for al_owned_key in (
        "min_brightness",
        "max_brightness",
        "sleep_brightness",
        "sleep_rgb_or_color_temp",
        "transition",
        "take_over_control",
    ):
        assert not is_managed_adaptive_lighting_owned_option_key(al_owned_key)


def test_managed_adaptive_lighting_options_preserve_al_owned_tuning() -> None:
    """Reconciliation should update lights without clobbering AL behavior settings."""
    config = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling", "light.lamp"),
    )
    assert config is not None

    options = managed_adaptive_lighting_options(
        {
            "min_brightness": 20,
            "max_brightness": 80,
            "sleep_brightness": 5,
            "sleep_rgb_or_color_temp": "color_temp",
            "lights": ["light.old_member"],
        },
        config,
    )

    assert options == {
        "min_brightness": 20,
        "max_brightness": 80,
        "sleep_brightness": 5,
        "sleep_rgb_or_color_temp": "color_temp",
        "lights": ["light.ceiling", "light.lamp"],
    }


def test_managed_adaptive_lighting_entry_ownership_requires_prefix_and_unique_id() -> (
    None
):
    """Reconciliation should not claim arbitrary user-created AL entries."""
    managed = ExistingAdaptiveLightingConfigEntry(
        entry_id="managed-1",
        unique_id="Magic Areas Living Room overhead",
        title="Magic Areas Living Room overhead",
        data={
            "name": "Magic Areas Living Room overhead",
            MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
            MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
        },
        options={},
    )
    user_named_like_ma = ExistingAdaptiveLightingConfigEntry(
        entry_id="user-1",
        unique_id="user-owned-id",
        title="Magic Areas Living Room overhead",
        data={"name": "Magic Areas Living Room overhead"},
        options={},
    )
    unrelated = ExistingAdaptiveLightingConfigEntry(
        entry_id="user-2",
        unique_id="Living Room",
        title="Living Room",
        data={"name": "Living Room"},
        options={},
    )

    assert is_managed_adaptive_lighting_entry(managed)
    assert not is_managed_adaptive_lighting_entry(user_named_like_ma)
    assert not is_managed_adaptive_lighting_entry(unrelated)


def test_managed_adaptive_lighting_reconcile_plan_creates_missing_entry() -> None:
    """Missing desired MA-owned AL configs should produce create operations."""
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling",),
    )
    assert desired is not None

    plan = managed_adaptive_lighting_reconcile_plan(
        desired_configs=(desired,),
        existing_entries=(),
    )

    assert len(plan) == 1
    assert plan[0].action is ManagedAdaptiveLightingReconcileAction.CREATE
    assert plan[0].data == {
        "name": "Magic Areas Living Room overhead",
        MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
        MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
    }
    assert plan[0].options == {"lights": ["light.ceiling"]}


def test_managed_adaptive_lighting_reconcile_plan_updates_lights_only() -> None:
    """Updates should preserve AL/user-owned options while syncing membership."""
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling", "light.lamp"),
    )
    assert desired is not None
    existing = ExistingAdaptiveLightingConfigEntry(
        entry_id="managed-1",
        unique_id="Magic Areas Living Room overhead",
        title="Magic Areas Living Room overhead",
        data={
            "name": "Magic Areas Living Room overhead",
            MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
            MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
        },
        options={
            "lights": ["light.old_member"],
            "min_brightness": 10,
            "sleep_rgb_or_color_temp": "color_temp",
        },
    )

    plan = managed_adaptive_lighting_reconcile_plan(
        desired_configs=(desired,),
        existing_entries=(existing,),
    )

    assert len(plan) == 1
    assert plan[0].action is ManagedAdaptiveLightingReconcileAction.UPDATE
    assert plan[0].existing_entry == existing
    assert plan[0].options == {
        "lights": ["light.ceiling", "light.lamp"],
        "min_brightness": 10,
        "sleep_rgb_or_color_temp": "color_temp",
    }


def test_managed_adaptive_lighting_reconcile_plan_deletes_stale_owned_entry() -> None:
    """Stale MA-owned entries should be removed while user entries are ignored."""
    stale = ExistingAdaptiveLightingConfigEntry(
        entry_id="managed-stale",
        unique_id="Magic Areas Living Room task",
        title="Magic Areas Living Room task",
        data={
            "name": "Magic Areas Living Room task",
            MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
            MANAGED_ADAPTIVE_LIGHTING_ROLE: "task_lights",
        },
        options={"lights": ["light.task"]},
    )
    user_entry = ExistingAdaptiveLightingConfigEntry(
        entry_id="user-entry",
        unique_id="Living Room",
        title="Living Room",
        data={"name": "Living Room"},
        options={"lights": ["light.user"]},
    )

    plan = managed_adaptive_lighting_reconcile_plan(
        desired_configs=(),
        existing_entries=(stale, user_entry),
    )

    assert len(plan) == 1
    assert plan[0].action is ManagedAdaptiveLightingReconcileAction.DELETE
    assert plan[0].existing_entry == stale


def test_managed_adaptive_lighting_reconcile_plan_scopes_deletes_by_area() -> None:
    """Per-area reconciliation must not delete managed AL entries for other areas."""
    other_area = ExistingAdaptiveLightingConfigEntry(
        entry_id="managed-bedroom",
        unique_id="Magic Areas Bedroom overhead",
        title="Magic Areas Bedroom overhead",
        data={
            "name": "Magic Areas Bedroom overhead",
            MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "bedroom",
            MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
        },
        options={"lights": ["light.bedroom"]},
    )

    assert (
        managed_adaptive_lighting_reconcile_plan(
            desired_configs=(),
            existing_entries=(other_area,),
            area_id="living_room",
        )
        == ()
    )


def test_managed_adaptive_lighting_reconcile_plan_is_noop_when_current() -> None:
    """Current MA-owned entries should not reload churn."""
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling",),
    )
    assert desired is not None
    existing = ExistingAdaptiveLightingConfigEntry(
        entry_id="managed-current",
        unique_id="Magic Areas Living Room overhead",
        title="Magic Areas Living Room overhead",
        data={
            "name": "Magic Areas Living Room overhead",
            MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
            MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
        },
        options={"lights": ["light.ceiling"], "min_brightness": 10},
    )

    assert (
        managed_adaptive_lighting_reconcile_plan(
            desired_configs=(desired,),
            existing_entries=(existing,),
        )
        == ()
    )


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


def test_discovery_candidates_can_list_all_complete_area_switch_sets() -> None:
    """Config flows need all same-area AL choices rather than one unambiguous match."""
    kitchen_refs = adaptive_lighting_switch_entity_ids("Kitchen")
    dining_refs = adaptive_lighting_switch_entity_ids("Dining")
    bedroom_refs = adaptive_lighting_switch_entity_ids("Bedroom")

    switch_sets = switch_sets_from_discovery_candidates(
        area_id="kitchen",
        candidates=(
            *(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="kitchen")
                for entity_id in kitchen_refs.values()
            ),
            *(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="kitchen")
                for entity_id in dining_refs.values()
            ),
            *(
                AdaptiveLightingSwitchCandidate(entity_id=entity_id, area_id="bedroom")
                for entity_id in bedroom_refs.values()
            ),
        ),
    )

    assert tuple(switch_set.main_switch_entity_id for switch_set in switch_sets) == (
        "switch.adaptive_lighting_dining",
        "switch.adaptive_lighting_kitchen",
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


def test_state_coordination_intents_track_sleep_and_accent_transitions() -> None:
    """State-transition combiner should emit only changed AL coordination intents."""
    switch_set = _switch_set()

    intents = adaptive_lighting_state_coordination_intents(
        switch_set,
        new_states=("sleep", "accented"),
        lost_states=(),
    )

    assert tuple(intent.service for intent in intents) == (
        SERVICE_TURN_ON,
        SERVICE_TURN_OFF,
        SERVICE_TURN_OFF,
    )
    assert tuple(intent.data[ATTR_ENTITY_ID] for intent in intents) == (
        "switch.adaptive_lighting_sleep_mode_kitchen",
        "switch.adaptive_lighting_adapt_brightness_kitchen",
        "switch.adaptive_lighting_adapt_color_kitchen",
    )
    assert tuple(intent.reason for intent in intents) == (
        AdaptiveLightingCoordinationReason.SLEEP_ACTIVE,
        AdaptiveLightingCoordinationReason.ACCENT_ACTIVE,
        AdaptiveLightingCoordinationReason.ACCENT_ACTIVE,
    )

    cleared_intents = adaptive_lighting_state_coordination_intents(
        switch_set,
        new_states=(),
        lost_states=("sleep", "accented"),
    )

    assert tuple(intent.service for intent in cleared_intents) == (
        SERVICE_TURN_OFF,
        SERVICE_TURN_ON,
        SERVICE_TURN_ON,
    )
    assert tuple(intent.reason for intent in cleared_intents) == (
        AdaptiveLightingCoordinationReason.SLEEP_CLEARED,
        AdaptiveLightingCoordinationReason.ACCENT_CLEARED,
        AdaptiveLightingCoordinationReason.ACCENT_CLEARED,
    )


def test_state_coordination_intents_ignore_stable_states() -> None:
    """Stable current states should not produce duplicate AL service intents."""
    assert (
        adaptive_lighting_state_coordination_intents(
            _switch_set(),
            new_states=("occupied",),
            lost_states=(),
        )
        == ()
    )
