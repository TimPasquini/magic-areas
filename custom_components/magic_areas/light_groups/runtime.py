"""Runtime and lifecycle helpers for light-group entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from time import monotonic
from typing import Protocol, TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sun.const import STATE_ABOVE_HORIZON
from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
    evaluate_and_execute_control_group_policy_sync,
    execute_control_group_runtime_effects,
    read_area_presence_states,
    register_area_and_group_state_listeners,
    resolve_area_presence_states,
)
from custom_components.magic_areas.core.control_intents import (
    AdaptiveLightingSwitchSet,
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    IntentAction,
    IntentReason,
    RoleTarget,
    adaptive_lighting_manual_restore_intents,
    adaptive_lighting_state_coordination_intents,
    async_execute_adaptive_lighting_intents,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_light_group_id,
)
from custom_components.magic_areas.core.managed_surface_registry import (
    resolve_managed_surface_entity_id,
)
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.light_groups.policy import CommandEchoState
from custom_components.magic_areas.light_groups.policy import (
    LightAction,
    LightPolicySignals,
)
from custom_components.magic_areas.light_groups.intent_adapter import (
    evaluate_light_member_suppression,
)
from custom_components.magic_areas.light_groups.config import (
    LIGHT_GROUP_PRESETS,
    feature_string_list,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from custom_components.magic_areas.light_groups.policy import (
        LightControlGroupPolicy,
    )


class _LightGroupHost(Protocol):
    """Runtime contract required by light-group helpers."""

    _attr_extra_state_attributes: dict[str, object]
    _attr_is_on: bool | None
    _listeners_initialized: bool
    _last_known_area_states: list[str]
    _last_known_area_states_from_dispatcher: bool
    _bright_since_monotonic: float | None
    _last_turn_on_monotonic: float | None
    _last_control_activity_monotonic: float | None
    _last_direct_light_activity_monotonic: float | None
    _ambient_rise_trend_contaminated: bool
    _inside_lux_samples: list[tuple[float, float]]
    _child_categories: list[str]
    _child_ids: list[str] | None
    _entity_ids: list[str]
    _feature_config: dict[str, object]
    _adaptive_lighting_switch_set: AdaptiveLightingSwitchSet | None
    _ambient_rise_signal_unique_id: str | None
    _area_id: str
    category: str | None
    hass: HomeAssistant
    logger: logging.Logger
    policy: LightControlGroupPolicy

    @property
    def _echo_state(self) -> CommandEchoState: ...

    @property
    def controlling(self) -> bool: ...

    @property
    def is_on(self) -> bool | None: ...

    @property
    def entity_id(self) -> str: ...

    @property
    def unique_id(self) -> str | None: ...

    @property
    def name(self) -> object: ...

    async def async_get_last_state(self) -> State | None: ...
    async def _setup_listeners(self) -> None: ...
    def current_control_target_is_on(self) -> bool | None: ...
    def _dispatch_light_action(
        self,
        action: LightAction,
        target_entity_ids: tuple[str, ...] | None = None,
    ) -> None: ...
    def light_member_suppression_members(
        self,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...
    def _reset_control_state(self) -> None: ...
    def _set_echo_state(self, state: CommandEchoState) -> None: ...
    def async_write_ha_state(self) -> None: ...
    def is_control_enabled(self) -> bool: ...
    def adaptive_lighting_switch_set(self) -> AdaptiveLightingSwitchSet | None: ...
    def track_group_listener(
        self, remove_listener: Callable[[], None], name: str
    ) -> None: ...
    def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool: ...
    def group_state_changed(self, event: Event[EventStateChangedData]) -> bool: ...


class AreaStateHandler(Protocol):
    """Callable contract for area-state dispatcher callbacks."""

    def __call__(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> object:
        """Handle one area-state event payload."""
        ...


def restore_group_state(host: _LightGroupHost, last_state: State | None) -> None:
    """Restore basic on/off + control state from last HA state object."""
    if not last_state:
        host._attr_is_on = False
        return

    host.logger.debug("%s: State restored [state=%s]", host.name, last_state.state)
    host._attr_is_on = last_state.state == STATE_ON

    if "controlling" in last_state.attributes:
        host._set_echo_state(
            CommandEchoState(
                owner_id=host.unique_id,
                controlling=last_state.attributes["controlling"],
                awaiting_echo=False,
            )
        )


async def setup_group(host: _LightGroupHost) -> None:
    """Set up light-group runtime state, restoration, and listeners."""
    attrs = dict(host._attr_extra_state_attributes or {})
    host._attr_extra_state_attributes = attrs

    if host.category == LightGroupCategory.ALL and host._child_categories:
        host._child_ids = _resolve_light_child_policy_entity_ids(host)
        attrs["child_ids"] = host._child_ids

    last_state = await host.async_get_last_state()
    restore_group_state(host, last_state)

    attrs["lights"] = host._entity_ids
    attrs["controlling"] = host.controlling
    await host._setup_listeners()
    if AreaStates.OCCUPIED.value not in host._last_known_area_states:
        host._reset_control_state()
        attrs["controlling"] = host.controlling


def _resolve_light_child_policy_entity_ids(host: _LightGroupHost) -> list[str]:
    """Resolve child policy entities by stable light-group unique IDs."""
    entity_registry = er.async_get(host.hass)
    child_ids: list[str] = []
    for category in host._child_categories:
        entity_id = entity_registry.async_get_entity_id(
            LIGHT_DOMAIN,
            DOMAIN,
            build_light_group_id(area_id=host._area_id, category=category),
        )
        if entity_id is not None:
            child_ids.append(entity_id)
    return child_ids


def setup_listeners(host: _LightGroupHost) -> None:
    """Set up area and group listeners once for this light group."""
    if host._listeners_initialized:
        return

    host._last_known_area_states = read_area_presence_states(
        host.hass,
        host._area_id,
    )
    host._last_known_area_states_from_dispatcher = False
    if host.current_control_target_is_on() and host._last_turn_on_monotonic is None:
        host._last_turn_on_monotonic = monotonic()
    register_area_and_group_state_listeners(
        hass=host.hass,
        track_listener=host.track_group_listener,
        area_state_handler=host.area_state_changed,
        group_entity_id=host.entity_id,
        group_state_handler=host.group_state_changed,
    )
    host.track_group_listener(
        async_track_state_change_event(
            host.hass,
            tuple(_direct_light_activity_entity_ids(host)),
            lambda event: handle_direct_light_state_change(host, event),
        ),
        "direct_light_activity",
    )
    ambient_rise_entity_id = _ambient_rise_signal_entity_id(host)
    if ambient_rise_entity_id is not None:
        host.track_group_listener(
            async_track_state_change_event(
                host.hass,
                (ambient_rise_entity_id,),
                lambda event: handle_ambient_rise_signal_state_change(host, event),
            ),
            "ambient_rise_signal",
        )
    ambient_source_entity_id = _ambient_rise_source_entity_id(host)
    if ambient_source_entity_id is not None:
        host.track_group_listener(
            async_track_state_change_event(
                host.hass,
                (ambient_source_entity_id,),
                lambda event: handle_ambient_rise_source_state_change(host, event),
            ),
            "ambient_rise_source",
        )
    host._listeners_initialized = True


ON_OFF_STATES = (STATE_ON, STATE_OFF)


@dataclass(frozen=True, slots=True)
class _IntentDispatchPlan:
    """Runtime intent target metadata for light dispatch observability."""

    target_entity_ids: tuple[str, ...] | None = None
    allowed_entity_ids: tuple[str, ...] = ()
    suppressed_entity_ids: tuple[str, ...] = ()
    reason: str = IntentReason.INTENT_ALLOWED.value


def evaluate_state_change(
    host: _LightGroupHost,
    states_tuple: tuple[list[str], list[str], list[str]],
    *,
    is_primary: bool,
) -> bool:
    """Evaluate and apply light-group policy decision for a state transition."""
    new_states, lost_states, current_states = states_tuple
    _update_bright_tracking(host, new_states, lost_states, current_states)

    now = monotonic()
    _update_inside_lux_tracking(host, now)
    bright_dwell_required = int(getattr(host.policy.policy, "bright_dwell_seconds", 0))
    min_on_required = int(getattr(host.policy.policy, "bright_min_on_seconds", 0))
    bright_dwell_met = (
        True
        if bright_dwell_required <= 0
        else (
            host._bright_since_monotonic is not None
            and (now - host._bright_since_monotonic) >= bright_dwell_required
        )
    )
    min_on_met = (
        True
        if min_on_required <= 0
        else (
            host._last_turn_on_monotonic is not None
            and (now - host._last_turn_on_monotonic) >= min_on_required
        )
    )
    inside_bright_met = _inside_bright_met(host)
    outside_context_ok = _outside_context_ok(host)
    ambient_rise_met = _ambient_rise_met(host, now)
    attribution_hold_required = int(
        getattr(host.policy.policy, "bright_attribution_hold_seconds", 0)
    )
    attribution_hold_met = (
        True
        if attribution_hold_required <= 0
        else (
            host._last_control_activity_monotonic is None
            or (now - host._last_control_activity_monotonic)
            >= attribution_hold_required
        )
    )
    host._attr_extra_state_attributes["adaptive_guards"] = {
        "bright_dwell_met": bright_dwell_met,
        "min_on_met": min_on_met,
        "inside_bright_met": inside_bright_met,
        "outside_context_ok": outside_context_ok,
        "attribution_hold_met": attribution_hold_met,
        "ambient_rise_met": ambient_rise_met,
        "ambient_rise_direct_light_blocked": _ambient_rise_direct_light_blocked(
            host, now
        ),
    }

    context = ControlGroupContext(
        group_id=host.entity_id,
        new_states=tuple(new_states),
        lost_states=tuple(lost_states),
        current_states=tuple(current_states),
        signals=LightPolicySignals(
            is_primary=is_primary,
            control_state=host._echo_state,
            bright_dwell_met=bright_dwell_met,
            min_on_met=min_on_met,
            inside_bright_met=inside_bright_met,
            outside_context_ok=outside_context_ok,
            attribution_hold_met=attribution_hold_met,
            ambient_rise_met=ambient_rise_met,
        ),
    )
    decision, executed = evaluate_and_execute_control_group_policy_sync(
        policy=host.policy,
        context=context,
        execute_decision=lambda decision: apply_decision(host, decision),
        logger=host.logger,
        actor_name=str(host.name),
    )
    _schedule_adaptive_bright_recheck_if_needed(host, decision.reason, current_states)
    return bool(executed)


def handle_area_state_change(
    host: _LightGroupHost,
    area_id: str,
    states_tuple: tuple[list[str], list[str], list[str]],
) -> bool:
    """Handle one AREA_STATE_CHANGED event for a light group."""
    if area_id != host._area_id:
        host.logger.debug(
            "%s: Area state change event not for us. Skipping. (req: %s/self: %s)",
            host.name,
            area_id,
            host._area_id,
        )
        return False

    if not host.is_control_enabled():
        host.logger.debug(
            "%s: Automatic control for light group is disabled, skipping...",
            host.name,
        )
        return False

    host.logger.debug("%s: Light group detected area state change", host.name)
    _new_states, _lost_states, current_states = states_tuple
    host._last_known_area_states = list(current_states)
    host._last_known_area_states_from_dispatcher = True
    schedule_adaptive_lighting_state_coordination(host, states_tuple)

    return evaluate_state_change(
        host,
        states_tuple,
        is_primary=host.category == LightGroupCategory.ALL,
    )


def apply_decision(host: _LightGroupHost, decision: ControlGroupDecision) -> bool:
    """Apply one policy decision and any runtime effects."""
    host._attr_extra_state_attributes["last_policy_reason"] = decision.reason
    execute_control_group_runtime_effects(
        decision,
        on_runtime_effect=lambda effect: apply_runtime_effect(host, effect),
    )

    if decision.action_type == ControlActionType.ACTIVATE:
        return turn_on(host)
    if decision.action_type == ControlActionType.DEACTIVATE:
        return turn_off(host)
    return False


def schedule_adaptive_lighting_state_coordination(
    host: _LightGroupHost,
    states_tuple: tuple[list[str], list[str], list[str]],
) -> bool:
    """Schedule Adaptive Lighting coordination for area-state transitions."""
    switch_set = _current_adaptive_lighting_switch_set(host)
    if switch_set is None:
        return False

    new_states, lost_states, _current_states = states_tuple
    intents = adaptive_lighting_state_coordination_intents(
        switch_set,
        new_states=new_states,
        lost_states=lost_states,
    )
    if not intents:
        return False

    host.hass.async_create_task(
        async_execute_adaptive_lighting_intents(host.hass, intents)
    )
    return True


def schedule_adaptive_lighting_manual_restore(host: _LightGroupHost) -> bool:
    """Schedule AL manual-control restore after MA control has been reset."""
    switch_set = _current_adaptive_lighting_switch_set(host)
    if switch_set is None:
        return False

    intents = adaptive_lighting_manual_restore_intents(
        switch_set,
        light_entity_ids=tuple(host._entity_ids),
        cooldown_expired=True,
    )
    if not intents:
        return False

    host.hass.async_create_task(
        async_execute_adaptive_lighting_intents(host.hass, intents)
    )
    return True


def _current_adaptive_lighting_switch_set(
    host: _LightGroupHost,
) -> AdaptiveLightingSwitchSet | None:
    """Resolve the current AL switch set, allowing late AL entity availability."""
    resolver = getattr(host, "adaptive_lighting_switch_set", None)
    if callable(resolver):
        switch_set = resolver()
    else:
        switch_set = getattr(host, "_adaptive_lighting_switch_set", None)
    return switch_set if isinstance(switch_set, AdaptiveLightingSwitchSet) else None


def apply_runtime_effect(
    host: _LightGroupHost,
    effect: ControlRuntimeEffect,
) -> None:
    """Apply a single runtime effect attached to a policy decision."""
    if (
        effect.effect_type == ControlRuntimeEffectType.SET_STATE
        and effect.namespace == "command_echo"
        and effect.key == "state"
        and isinstance(effect.value, CommandEchoState)
    ):
        should_restore_al_manual_control = (
            not host._echo_state.controlling and effect.value.controlling
        )
        host._set_echo_state(effect.value)
        if should_restore_al_manual_control:
            schedule_adaptive_lighting_manual_restore(host)


def is_valid_origin_state_toggle(origin_event: object | None) -> bool:
    """Return True when origin event is a real on/off state toggle."""
    if not origin_event:
        return True
    event_type = getattr(origin_event, "event_type", None)
    if event_type != "state_changed":
        return True

    event_data = getattr(origin_event, "data", None)
    if not isinstance(event_data, dict):
        return True
    old_state = event_data.get("old_state")
    new_state = event_data.get("new_state")
    if not old_state or not old_state.state or old_state.state not in ON_OFF_STATES:
        return False
    if not new_state or not new_state.state or new_state.state not in ON_OFF_STATES:
        return False
    if old_state.state == new_state.state:
        return False
    if old_state.attributes.get("restored"):
        return False
    return True


def handle_group_state_change(
    host: _LightGroupHost, event: Event[EventStateChangedData]
) -> bool:
    """Handle one state_changed event for a light group entity itself."""
    if not event.context:
        return False

    origin_event = event.context.origin_event
    if host.category != LightGroupCategory.ALL:
        if _is_origin_light_attribute_change(origin_event):
            host._last_control_activity_monotonic = monotonic()
            host._attr_extra_state_attributes["controlling"] = host.controlling
            host.async_write_ha_state()
            return True
        if not is_valid_origin_state_toggle(origin_event):
            return False

    current_area_states = _current_area_states_for_group_event(host)

    if AreaStates.OCCUPIED.value not in current_area_states:
        if (
            host.category != LightGroupCategory.ALL
            and _origin_new_state(origin_event) == STATE_ON
        ):
            if not process_secondary_group_state_change(host, origin_event):
                return False
        else:
            host._reset_control_state()
            schedule_adaptive_lighting_manual_restore(host)
            host.logger.debug("%s: Control Reset.", host.name)
    elif host.category == LightGroupCategory.ALL:
        if host._child_ids:
            controlling = any(
                bool(entity_state.attributes.get("controlling"))
                for entity_id in host._child_ids
                if (entity_state := host.hass.states.get(entity_id))
            )
            host._set_echo_state(host._echo_state.set_controlling(controlling))
    else:
        if not process_secondary_group_state_change(host, origin_event):
            return False

    host._attr_extra_state_attributes["controlling"] = host.controlling
    host.async_write_ha_state()
    return True


def handle_direct_light_state_change(
    host: _LightGroupHost, event: Event[EventStateChangedData]
) -> bool:
    """Track direct member-light output changes that can contaminate lux trends."""
    if not _direct_light_output_changed(
        event.data.get("old_state"),
        event.data.get("new_state"),
    ):
        return False

    host._last_direct_light_activity_monotonic = monotonic()
    host._ambient_rise_trend_contaminated = True
    host._attr_extra_state_attributes["last_direct_light_activity_entity_id"] = (
        event.data.get("entity_id")
    )
    return True


def _direct_light_activity_entity_ids(host: _LightGroupHost) -> tuple[str, ...]:
    """Return configured room lights whose output can contaminate lux trends."""
    entity_ids: list[str] = [str(entity_id) for entity_id in host._entity_ids]
    feature_config = getattr(host, "_feature_config", {})
    if isinstance(feature_config, dict):
        for preset in LIGHT_GROUP_PRESETS:
            entity_ids.extend(feature_string_list(feature_config, preset.category))
    return tuple(dict.fromkeys(entity_ids))


def handle_ambient_rise_signal_state_change(
    host: _LightGroupHost, event: Event[EventStateChangedData]
) -> bool:
    """Clear direct-light contamination and re-evaluate when Trend evidence changes."""
    new_state = event.data.get("new_state")
    if new_state is None:
        return False

    if new_state.state != STATE_ON:
        host._ambient_rise_trend_contaminated = False
    if not host.is_control_enabled():
        return False

    current_states = read_area_presence_states(host.hass, host._area_id)
    current_state_values = {str(state) for state in current_states}
    if (
        AreaStates.OCCUPIED.value not in current_state_values
        or AreaStates.BRIGHT.value not in current_state_values
    ):
        return False

    return host.area_state_changed(host._area_id, ([], [], current_states))


def handle_ambient_rise_source_state_change(
    host: _LightGroupHost, event: Event[EventStateChangedData]
) -> bool:
    """Re-evaluate adaptive bright policy when the ambient source changes."""
    if event.data.get("new_state") is None:
        return False
    if not host.is_control_enabled():
        return False

    current_states = read_area_presence_states(host.hass, host._area_id)
    current_state_values = {str(state) for state in current_states}
    if (
        AreaStates.OCCUPIED.value not in current_state_values
        or AreaStates.BRIGHT.value not in current_state_values
    ):
        return False

    return host.area_state_changed(host._area_id, ([], [], current_states))


def _current_area_states_for_group_event(host: _LightGroupHost) -> list[str]:
    """Resolve area states for group self-events without overriding fresh cache."""
    if host._last_known_area_states_from_dispatcher and host._last_known_area_states:
        return list(host._last_known_area_states)
    return resolve_area_presence_states(
        hass=host.hass,
        area_id=host._area_id,
        require_occupied=True,
    )


def process_secondary_group_state_change(
    host: _LightGroupHost, origin_event: object | None
) -> bool:
    """Validate and apply secondary group-state change handling."""
    if not is_valid_origin_state_toggle(origin_event):
        return False
    if host._echo_state.awaiting_echo:
        host.logger.debug("%s: Group controlled by us.", host.name)
        host._set_echo_state(host._echo_state.command_completed())
    else:
        host.logger.debug("%s: Group controlled by something else.", host.name)
        host._set_echo_state(host._echo_state.external_change())

    if _origin_new_state(origin_event) == STATE_ON:
        host._last_turn_on_monotonic = monotonic()
    return True


def turn_on(host: _LightGroupHost) -> bool:
    """Turn on light if it's not already on and if we're controlling it."""
    return _dispatch_controlled_action(host, LightAction.TURN_ON, when_is_on=False)


def turn_off(host: _LightGroupHost) -> bool:
    """Turn off light if it's not already off, and we're controlling it."""
    return _dispatch_controlled_action(host, LightAction.TURN_OFF, when_is_on=True)


def _dispatch_controlled_action(
    host: _LightGroupHost,
    action: LightAction,
    *,
    when_is_on: bool,
) -> bool:
    """Dispatch one light action when control is enabled and on/off state matches."""
    if not host._echo_state.controlling:
        _set_last_intent_attributes(
            host,
            action=action,
            reason="control_disabled",
            executed=False,
        )
        return False

    dispatch_plan = _intent_dispatch_plan(host, action)
    target_entity_ids = dispatch_plan.target_entity_ids
    target_is_on = (
        _explicit_target_is_on(host, target_entity_ids)
        if target_entity_ids is not None
        else host.current_control_target_is_on()
    )
    if target_entity_ids == ():
        _set_last_intent_attributes(
            host,
            action=action,
            reason=dispatch_plan.reason,
            executed=False,
            target_entity_ids=(),
            allowed_entity_ids=dispatch_plan.allowed_entity_ids,
            suppressed_entity_ids=dispatch_plan.suppressed_entity_ids,
        )
        return False
    if target_is_on is not None and target_is_on != when_is_on:
        _set_last_intent_attributes(
            host,
            action=action,
            reason="target_state_mismatch",
            executed=False,
            target_entity_ids=target_entity_ids or (),
            allowed_entity_ids=dispatch_plan.allowed_entity_ids,
            suppressed_entity_ids=dispatch_plan.suppressed_entity_ids,
            target_is_on=target_is_on,
            expected_target_is_on=when_is_on,
        )
        return False

    host._set_echo_state(host._echo_state.command_issued(host.unique_id))
    host._last_control_activity_monotonic = monotonic()
    if action == LightAction.TURN_ON:
        host._last_turn_on_monotonic = monotonic()
    _set_last_intent_attributes(
        host,
        action=action,
        reason=dispatch_plan.reason,
        executed=True,
        target_entity_ids=target_entity_ids or (),
        allowed_entity_ids=dispatch_plan.allowed_entity_ids,
        suppressed_entity_ids=dispatch_plan.suppressed_entity_ids,
        target_is_on=target_is_on,
        expected_target_is_on=when_is_on,
    )
    if target_entity_ids is None:
        host._dispatch_light_action(action)
    else:
        host._dispatch_light_action(action, target_entity_ids)
    return True


def _intent_dispatch_plan(
    host: _LightGroupHost,
    action: LightAction,
) -> _IntentDispatchPlan:
    """Return suppression-aware dispatch target metadata."""
    current_states = tuple(getattr(host, "_last_known_area_states", ()))
    if (
        AreaStates.SLEEP not in current_states
        and AreaStates.ACCENT not in current_states
    ):
        return _IntentDispatchPlan()

    sleep_entity_ids, accent_entity_ids = host.light_member_suppression_members()
    source_entity_ids = tuple(host._entity_ids)
    target = RoleTarget(
        role=str(host.category or LightGroupCategory.ALL),
        domain=LIGHT_DOMAIN,
        area_id=host._area_id,
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.CONFIG_RECONCILIATION,
        entity_ids=source_entity_ids,
    )
    decision = evaluate_light_member_suppression(
        target=target,
        current_states=current_states,
        sleep_entity_ids=sleep_entity_ids,
        accent_entity_ids=accent_entity_ids,
        action=_intent_action_for_light_action(action),
    )
    if decision.reason is IntentReason.INTENT_ALLOWED:
        if action is LightAction.TURN_OFF:
            return _IntentDispatchPlan(
                target_entity_ids=(),
                allowed_entity_ids=source_entity_ids,
                reason=decision.reason.value,
            )
        return _IntentDispatchPlan(reason=decision.reason.value)
    if decision.target_entity_ids == source_entity_ids:
        return _IntentDispatchPlan(
            allowed_entity_ids=decision.target_entity_ids,
            reason=decision.reason.value,
        )

    surviving_entity_ids = set(decision.target_entity_ids)
    suppressed_entity_ids = tuple(
        entity_id
        for entity_id in source_entity_ids
        if entity_id not in surviving_entity_ids
    )
    if action is LightAction.TURN_OFF:
        return _IntentDispatchPlan(
            target_entity_ids=suppressed_entity_ids,
            allowed_entity_ids=decision.target_entity_ids,
            suppressed_entity_ids=suppressed_entity_ids,
            reason=decision.reason.value,
        )
    return _IntentDispatchPlan(
        target_entity_ids=decision.target_entity_ids,
        allowed_entity_ids=decision.target_entity_ids,
        suppressed_entity_ids=suppressed_entity_ids,
        reason=decision.reason.value,
    )


def _set_last_intent_attributes(
    host: _LightGroupHost,
    *,
    action: LightAction,
    reason: str,
    executed: bool,
    target_entity_ids: tuple[str, ...] = (),
    allowed_entity_ids: tuple[str, ...] = (),
    suppressed_entity_ids: tuple[str, ...] = (),
    target_is_on: bool | None = None,
    expected_target_is_on: bool | None = None,
) -> None:
    """Expose concise last-intent diagnostics on light-group attributes."""
    attrs = getattr(host, "_attr_extra_state_attributes", None)
    if attrs is None:
        attrs = {}
        host._attr_extra_state_attributes = attrs

    attrs["last_intent_action"] = action.value
    attrs["last_intent_reason"] = reason
    attrs["last_intent_executed"] = executed
    attrs["last_intent_target_entity_ids"] = target_entity_ids
    attrs["last_intent_allowed_entity_ids"] = allowed_entity_ids
    attrs["last_intent_suppressed_entity_ids"] = suppressed_entity_ids
    if target_is_on is None:
        attrs.pop("last_intent_target_is_on", None)
    else:
        attrs["last_intent_target_is_on"] = target_is_on
    if expected_target_is_on is None:
        attrs.pop("last_intent_expected_target_is_on", None)
    else:
        attrs["last_intent_expected_target_is_on"] = expected_target_is_on


def _intent_action_for_light_action(action: LightAction) -> IntentAction:
    """Map light actions to generic intent actions."""
    if action is LightAction.TURN_ON:
        return IntentAction.ACTIVATE
    if action is LightAction.TURN_OFF:
        return IntentAction.DEACTIVATE
    return IntentAction.NOOP


def _explicit_target_is_on(
    host: _LightGroupHost,
    target_entity_ids: tuple[str, ...],
) -> bool | None:
    """Return helper-like on/off state for an explicit target subset."""
    if not target_entity_ids:
        return None
    any_on = False
    any_known = False
    for entity_id in target_entity_ids:
        state = host.hass.states.get(entity_id)
        if state is None or state.state not in ON_OFF_STATES:
            continue
        any_known = True
        if state.state == STATE_ON:
            any_on = True
    return any_on if any_known else None


def _origin_new_state(origin_event: object | None) -> str | None:
    """Return new state from origin event payload when available."""
    if not origin_event:
        return None
    event_data = getattr(origin_event, "data", None)
    if not isinstance(event_data, dict):
        return None
    new_state = event_data.get("new_state")
    if new_state is None:
        return None
    state = getattr(new_state, "state", None)
    return state if isinstance(state, str) else None


def _is_origin_light_attribute_change(origin_event: object | None) -> bool:
    """Return True when origin event reflects on->on brightness updates."""
    if not origin_event:
        return False
    event_type = getattr(origin_event, "event_type", None)
    if event_type != "state_changed":
        return False

    event_data = getattr(origin_event, "data", None)
    if not isinstance(event_data, dict):
        return False
    old_state = event_data.get("old_state")
    new_state = event_data.get("new_state")
    if old_state is None or new_state is None:
        return False
    if (
        getattr(old_state, "state", None) != STATE_ON
        or getattr(new_state, "state", None) != STATE_ON
    ):
        return False
    old_attrs = getattr(old_state, "attributes", {})
    new_attrs = getattr(new_state, "attributes", {})
    if not isinstance(old_attrs, dict) or not isinstance(new_attrs, dict):
        return False
    return _numeric_attr(old_attrs, "brightness") != _numeric_attr(
        new_attrs, "brightness"
    )


def _direct_light_output_changed(old_state: object | None, new_state: object | None) -> bool:
    """Return True when a light output change can affect in-room lux readings."""
    if old_state is None or new_state is None:
        return False
    old_value = getattr(old_state, "state", None)
    new_value = getattr(new_state, "state", None)
    if new_value != STATE_ON:
        return False
    if old_value == STATE_OFF:
        return True
    if old_value != STATE_ON:
        return False

    old_attrs = getattr(old_state, "attributes", {})
    new_attrs = getattr(new_state, "attributes", {})
    if not isinstance(old_attrs, dict) or not isinstance(new_attrs, dict):
        return False
    old_brightness = _numeric_attr(old_attrs, "brightness")
    new_brightness = _numeric_attr(new_attrs, "brightness")
    if (
        old_brightness is not None
        and new_brightness is not None
        and new_brightness > old_brightness
    ):
        return True

    return False


def _numeric_attr(attributes: dict[str, object], key: str) -> float | None:
    """Return a numeric state attribute when present."""
    value = attributes.get(key)
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _update_bright_tracking(
    host: _LightGroupHost,
    new_states: list[str],
    lost_states: list[str],
    current_states: list[str],
) -> None:
    """Track BRIGHT state timing for adaptive-policy safeguards."""
    now = monotonic()
    new_state_values = {str(state) for state in new_states}
    lost_state_values = {str(state) for state in lost_states}
    current_state_values = {str(state) for state in current_states}

    if AreaStates.CLEAR.value in new_state_values:
        host._bright_since_monotonic = None
        return
    if AreaStates.BRIGHT.value in new_state_values:
        host._bright_since_monotonic = now
        return
    if AreaStates.BRIGHT.value in lost_state_values:
        host._bright_since_monotonic = None
        return
    if (
        AreaStates.BRIGHT.value in current_state_values
        and host._bright_since_monotonic is None
    ):
        host._bright_since_monotonic = now


def _schedule_adaptive_bright_recheck_if_needed(
    host: _LightGroupHost,
    reason: str,
    current_states: list[str],
) -> None:
    """Schedule a stable-state recheck when adaptive bright guards need time."""
    ambient_poll_needed = _adaptive_ambient_poll_needed(host, current_states)
    if not reason.startswith("bright_adaptive_waiting_") and not ambient_poll_needed:
        return
    if AreaStates.BRIGHT.value not in {str(state) for state in current_states}:
        return

    delay = (
        1.0
        if ambient_poll_needed
        else _adaptive_bright_recheck_delay(host, reason)
    )
    if delay is None:
        return

    def recheck() -> None:
        live_states = read_area_presence_states(host.hass, host._area_id)
        recheck_states = list(live_states or host._last_known_area_states or current_states)
        host.area_state_changed(
            host._area_id,
            ([], [], recheck_states),
        )

    remove_listener = host.hass.loop.call_later(delay, recheck).cancel
    host.track_group_listener(remove_listener, "adaptive_bright_recheck")


def _adaptive_ambient_poll_needed(
    host: _LightGroupHost,
    current_states: list[str],
) -> bool:
    """Return whether managed ambient-rise evidence should be polled."""
    current_state_values = {str(state) for state in current_states}
    if (
        AreaStates.OCCUPIED.value not in current_state_values
        or AreaStates.BRIGHT.value not in current_state_values
    ):
        return False
    if str(getattr(host.policy.policy, "brightness_mode", "")) != "adaptive":
        return False
    if not bool(getattr(host.policy.policy, "adaptive_require_ambient_rise", False)):
        return False
    if _ambient_rise_signal_entity_id(host) is None:
        return False
    return host.current_control_target_is_on() is True


def _adaptive_bright_recheck_delay(
    host: _LightGroupHost,
    reason: str,
) -> float | None:
    """Return a bounded delay for an adaptive bright guard recheck."""
    now = monotonic()
    if reason == "bright_adaptive_waiting_dwell":
        required = int(getattr(host.policy.policy, "bright_dwell_seconds", 0))
        started = host._bright_since_monotonic
    elif reason == "bright_adaptive_waiting_min_on":
        required = int(getattr(host.policy.policy, "bright_min_on_seconds", 0))
        started = host._last_turn_on_monotonic
    elif reason == "bright_adaptive_attribution_hold":
        required = int(
            getattr(host.policy.policy, "bright_attribution_hold_seconds", 0)
        )
        started = host._last_control_activity_monotonic
    elif reason == "bright_adaptive_waiting_ambient_rise":
        return 1.0 if _ambient_rise_signal_entity_id(host) is not None else None
    else:
        return None

    if required <= 0:
        return 0.1
    if started is None:
        return None
    return max(0.1, (started + required) - now + 0.1)


def _outside_context_ok(host: _LightGroupHost) -> bool:
    """Return whether outside context allows adaptive bright-driven off."""
    outside_bright_entity = getattr(host.policy.policy, "outside_bright_entity", None)
    if isinstance(outside_bright_entity, str) and outside_bright_entity:
        outside_bright_state = host.hass.states.get(outside_bright_entity)
        return bool(outside_bright_state and outside_bright_state.state == STATE_ON)

    source = str(getattr(host.policy.policy, "outside_context_source", "sun")).lower()
    if source == "none":
        return False

    if source == "outside_lux":
        entity_id = getattr(host.policy.policy, "outside_lux_entity", None)
        if not isinstance(entity_id, str) or not entity_id:
            return False
        outside_state = host.hass.states.get(entity_id)
        if outside_state is None:
            return False
        try:
            outside_lux = float(outside_state.state)
        except (TypeError, ValueError):
            return False
        min_lux = int(getattr(host.policy.policy, "outside_lux_min", 0))
        if outside_lux < min_lux:
            return False

        delta_required = int(getattr(host.policy.policy, "outside_lux_inside_delta", 0))
        ratio_required_pct = int(
            getattr(host.policy.policy, "outside_lux_inside_ratio_min_percent", 0)
        )
        if delta_required <= 0 and ratio_required_pct <= 0:
            return True
        inside_entity = getattr(host.policy.policy, "outside_lux_inside_entity", None)
        if not isinstance(inside_entity, str) or not inside_entity:
            return False
        inside_state = host.hass.states.get(inside_entity)
        if inside_state is None:
            return False
        try:
            inside_lux = float(inside_state.state)
        except (TypeError, ValueError):
            return False
        if delta_required > 0 and (outside_lux - inside_lux) < delta_required:
            return False
        if ratio_required_pct <= 0:
            return True
        if inside_lux <= 0:
            return outside_lux > 0
        ratio = outside_lux / inside_lux
        return ratio >= (ratio_required_pct / 100.0)

    sun_state = host.hass.states.get("sun.sun")
    return bool(sun_state and sun_state.state == STATE_ABOVE_HORIZON)


def _inside_bright_met(host: _LightGroupHost) -> bool | None:
    """Return explicit inside-bright signal state when configured."""
    inside_bright_entity = getattr(host.policy.policy, "inside_bright_entity", None)
    if not isinstance(inside_bright_entity, str) or not inside_bright_entity:
        return None
    inside_bright_state = host.hass.states.get(inside_bright_entity)
    if inside_bright_state is None:
        return None
    if inside_bright_state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
        return None
    return inside_bright_state.state == STATE_ON


def _inside_lux_sample(host: _LightGroupHost) -> float | None:
    """Return inside lux sample from configured entity, if available."""
    entity_id = getattr(host.policy.policy, "outside_lux_inside_entity", None)
    if not isinstance(entity_id, str) or not entity_id:
        return None
    state = host.hass.states.get(entity_id)
    if state is None:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _update_inside_lux_tracking(host: _LightGroupHost, now: float) -> None:
    """Append latest inside-lux sample and prune old detector history."""
    sample = _inside_lux_sample(host)
    if sample is not None:
        host._inside_lux_samples.append((now, sample))

    window = int(getattr(host.policy.policy, "ambient_rise_window_seconds", 120))
    if window <= 0:
        host._inside_lux_samples = host._inside_lux_samples[-1:]
        return
    cutoff = now - window
    host._inside_lux_samples = [
        (ts, lux) for ts, lux in host._inside_lux_samples if ts >= cutoff
    ]


def _ambient_rise_met(host: _LightGroupHost, now: float) -> bool:
    """Return whether inside ambient rise evidence is sufficient."""
    require = bool(getattr(host.policy.policy, "adaptive_require_ambient_rise", False))
    if not require:
        return True

    managed_signal_state = _managed_ambient_rise_state(host)
    if managed_signal_state is not None:
        if managed_signal_state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            managed_signal_state = None
        elif managed_signal_state != STATE_ON:
            host._ambient_rise_trend_contaminated = False
            return False
        else:
            return not host._ambient_rise_trend_contaminated

    if managed_signal_state is None and _direct_light_activity_blocks_ambient_rise(
        host, now
    ):
        return False

    window = int(getattr(host.policy.policy, "ambient_rise_window_seconds", 120))
    delta_required = int(getattr(host.policy.policy, "ambient_rise_min_delta", 20))
    if window <= 0:
        return False
    if delta_required <= 0:
        return True

    if not host._inside_lux_samples:
        return False
    cutoff = now - window
    samples = [(ts, lux) for ts, lux in host._inside_lux_samples if ts >= cutoff]
    if len(samples) < 2:
        return False

    start_lux = min(lux for _, lux in samples)
    end_lux = samples[-1][1]
    return (end_lux - start_lux) >= delta_required


def _ambient_rise_direct_light_blocked(host: _LightGroupHost, now: float) -> bool:
    """Return whether direct-light contamination is actively blocking ambient rise."""
    managed_signal_state = _managed_ambient_rise_state(host)
    if managed_signal_state is not None:
        if managed_signal_state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return _direct_light_activity_blocks_ambient_rise(host, now)
        if managed_signal_state != STATE_ON:
            return False
        return bool(host._ambient_rise_trend_contaminated)
    return _direct_light_activity_blocks_ambient_rise(host, now)


def _direct_light_activity_blocks_ambient_rise(
    host: _LightGroupHost,
    now: float,
) -> bool:
    """Return whether direct-light activity contaminates the ambient trend window."""
    last_activity = getattr(host, "_last_direct_light_activity_monotonic", None)
    if (
        last_activity is None
        or isinstance(last_activity, bool)
        or not isinstance(last_activity, int | float)
    ):
        return False

    window = int(getattr(host.policy.policy, "ambient_rise_window_seconds", 120))
    if window <= 0:
        return False
    return bool((now - last_activity) < window)


def _ambient_rise_signal_entity_id(host: _LightGroupHost) -> str | None:
    """Return the managed Trend helper entity id when registered."""
    unique_id = getattr(host, "_ambient_rise_signal_unique_id", None)
    if not isinstance(unique_id, str) or not unique_id:
        return None

    entity_id = resolve_managed_surface_entity_id(
        host.hass,
        er.async_get(host.hass),
        unique_id=unique_id,
        entity_domain=BINARY_SENSOR_DOMAIN,
        config_entry_domain=TREND_DOMAIN,
    )
    return entity_id


def _ambient_rise_source_entity_id(host: _LightGroupHost) -> str | None:
    """Return the configured in-room lux source for ambient-rise triggering."""
    if str(getattr(host.policy.policy, "brightness_mode", "")) != "adaptive":
        return None
    if not bool(getattr(host.policy.policy, "adaptive_require_ambient_rise", False)):
        return None
    entity_id = getattr(host.policy.policy, "outside_lux_inside_entity", None)
    return entity_id if isinstance(entity_id, str) and entity_id else None


def _managed_ambient_rise_state(host: _LightGroupHost) -> str | None:
    """Return managed Trend helper state when the helper exists."""
    entity_id = _ambient_rise_signal_entity_id(host)
    if entity_id is None:
        return None

    state = host.hass.states.get(entity_id)
    if state is None:
        return None
    state_value = getattr(state, "state", None)
    return state_value if isinstance(state_value, str) else None


def _managed_ambient_rise_met(host: _LightGroupHost) -> bool | None:
    """Return managed Trend helper state when the helper has a usable value."""
    state = _managed_ambient_rise_state(host)
    if state is None or state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
        return None
    return state == STATE_ON
