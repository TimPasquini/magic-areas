"""Runtime and lifecycle helpers for light-group entities."""

from __future__ import annotations

from collections.abc import Callable
import logging
from time import monotonic
from typing import Protocol, TYPE_CHECKING

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sun.const import STATE_ABOVE_HORIZON
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, State
from homeassistant.helpers.event import EventStateChangedData

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
    resolve_group_entity_ids_for_metadata_values,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
    GroupMetadataKey,
)
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.light_groups.policy import CommandEchoState
from custom_components.magic_areas.light_groups.policy import (
    LightAction,
    LightPolicySignals,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.light_groups.policy import LightControlGroupPolicy


class _LightGroupHost(Protocol):
    """Runtime contract required by light-group helpers."""

    _attr_extra_state_attributes: dict[str, object]
    _attr_is_on: bool | None
    _listeners_initialized: bool
    _last_known_area_states: list[str]
    _bright_since_monotonic: float | None
    _last_turn_on_monotonic: float | None
    _last_control_activity_monotonic: float | None
    _inside_lux_samples: list[tuple[float, float]]
    _child_categories: list[str]
    _child_ids: list[str] | None
    _entity_ids: list[str]
    _area_id: str
    _coordinator: MagicAreasCoordinator
    category: str | None
    entity_id: str
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
    def unique_id(self) -> str | None: ...

    @property
    def name(self) -> object: ...

    async def async_get_last_state(self) -> State | None: ...
    async def _setup_listeners(self) -> None: ...
    def _dispatch_light_action(self, action: LightAction) -> None: ...
    def _reset_control_state(self) -> None: ...
    def _set_echo_state(self, state: CommandEchoState) -> None: ...
    def async_write_ha_state(self) -> None: ...
    def is_control_enabled(self) -> bool: ...
    def track_group_listener(self, remove_listener: Callable[[], None], name: str) -> None: ...
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
        group_registry = host._coordinator.data.group_registry if host._coordinator.data else None
        if group_registry is None:
            host._child_ids = []
        else:
            host._child_ids = resolve_group_entity_ids_for_metadata_values(
                host.hass,
                group_registry=group_registry,
                area_id=host._area_id,
                policy_id=str(ControlGroupPolicyId.LIGHT_GROUPS),
                domain=LIGHT_DOMAIN,
                metadata_key=str(GroupMetadataKey.CATEGORY),
                metadata_values=host._child_categories,
            )
        attrs["child_ids"] = host._child_ids

    last_state = await host.async_get_last_state()
    restore_group_state(host, last_state)

    attrs["lights"] = host._entity_ids
    attrs["controlling"] = host.controlling
    await host._setup_listeners()


def setup_listeners(host: _LightGroupHost) -> None:
    """Set up area and group listeners once for this light group."""
    if host._listeners_initialized:
        return

    host._last_known_area_states = read_area_presence_states(
        host.hass,
        host._area_id,
    )
    if host.is_on and host._last_turn_on_monotonic is None:
        host._last_turn_on_monotonic = monotonic()
    register_area_and_group_state_listeners(
        hass=host.hass,
        track_listener=host.track_group_listener,
        area_state_handler=host.area_state_changed,
        group_entity_id=host.entity_id,
        group_state_handler=host.group_state_changed,
    )
    host._listeners_initialized = True


ON_OFF_STATES = (STATE_ON, STATE_OFF)
LIGHT_ATTR_KEYS = (
    "brightness",
    "color_temp",
    "color_temp_kelvin",
    "hs_color",
    "rgb_color",
    "rgbw_color",
    "rgbww_color",
    "xy_color",
)

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
            or (now - host._last_control_activity_monotonic) >= attribution_hold_required
        )
    )
    host._attr_extra_state_attributes["adaptive_guards"] = {
        "bright_dwell_met": bright_dwell_met,
        "min_on_met": min_on_met,
        "outside_context_ok": outside_context_ok,
        "attribution_hold_met": attribution_hold_met,
        "ambient_rise_met": ambient_rise_met,
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
            outside_context_ok=outside_context_ok,
            attribution_hold_met=attribution_hold_met,
            ambient_rise_met=ambient_rise_met,
        ),
    )
    _decision, executed = evaluate_and_execute_control_group_policy_sync(
        policy=host.policy,
        context=context,
        execute_decision=lambda decision: apply_decision(host, decision),
        logger=host.logger,
        actor_name=str(host.name),
    )
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
        host._set_echo_state(effect.value)


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

    current_area_states = resolve_area_presence_states(
        hass=host.hass,
        area_id=host._area_id,
        cached_states=host._last_known_area_states,
        require_occupied=True,
    )

    if AreaStates.OCCUPIED.value not in current_area_states:
        host._reset_control_state()
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
        origin_event = event.context.origin_event
        if _is_origin_light_attribute_change(origin_event):
            host._last_control_activity_monotonic = monotonic()
            host._attr_extra_state_attributes["controlling"] = host.controlling
            host.async_write_ha_state()
            return True
        if not process_secondary_group_state_change(host, origin_event):
            return False

    host._attr_extra_state_attributes["controlling"] = host.controlling
    host.async_write_ha_state()
    return True


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
        return False
    if host.is_on != when_is_on:
        return False

    host._set_echo_state(host._echo_state.command_issued(host.unique_id))
    host._last_control_activity_monotonic = monotonic()
    if action == LightAction.TURN_ON:
        host._last_turn_on_monotonic = monotonic()
    host._dispatch_light_action(action)
    return True


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
    """Return True when origin event reflects on->on light attribute updates."""
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
    if getattr(old_state, "state", None) != STATE_ON or getattr(new_state, "state", None) != STATE_ON:
        return False
    old_attrs = getattr(old_state, "attributes", {})
    new_attrs = getattr(new_state, "attributes", {})
    if not isinstance(old_attrs, dict) or not isinstance(new_attrs, dict):
        return False
    return any(old_attrs.get(key) != new_attrs.get(key) for key in LIGHT_ATTR_KEYS)


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


def _outside_context_ok(host: _LightGroupHost) -> bool:
    """Return whether outside context allows adaptive bright-driven off."""
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
