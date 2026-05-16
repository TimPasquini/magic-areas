"""Non-entity runtime host for native-helper-backed light groups."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import EventStateChangedData

from custom_components.magic_areas.core.control_intents import (
    ControlTargetSource,
    resolve_role_target,
)
from custom_components.magic_areas.core.controls import execute_control_group_decision
from custom_components.magic_areas.core.listener_registry import ListenerRegistry
from custom_components.magic_areas.core.managed_surface_registry import (
    resolve_managed_surface_entity_id,
)
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.light_groups.config import (
    LightGroupPreset,
    adaptive_lighting_diagnostics,
    adaptive_lighting_switch_set,
    adaptive_require_ambient_rise,
    ambient_rise_min_delta,
    ambient_rise_window_seconds,
    bright_attribution_hold_seconds,
    bright_dwell_seconds,
    bright_min_on_seconds,
    brightness_mode,
    get_light_group_preset,
    inside_bright_entity,
    outside_bright_entity,
    outside_context_source,
    outside_lux_entity,
    outside_lux_inside_delta,
    outside_lux_inside_entity,
    outside_lux_inside_ratio_min_percent,
    outside_lux_min,
    preset_act_on_modes,
    preset_members,
    preset_states,
)
from custom_components.magic_areas.light_groups.identity import (
    LIGHT_GROUP_ROLE_LABELS,
    build_light_group_helper_surface_unique_id,
)
from custom_components.magic_areas.light_groups.policy import (
    CommandEchoState,
    LightAction,
    build_light_control_group_policy,
    light_action_to_control_group,
)
from custom_components.magic_areas.light_groups.runtime import (
    evaluate_state_change,
    handle_area_state_change,
    handle_group_state_change,
    setup_group,
)
from custom_components.magic_areas.light_groups.signals import ambient_rise_signal_surface

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import State

    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.core.runtime_model import AreaConfig

GROUP_DOMAIN = "group"
_LOGGER = logging.getLogger(__name__)


class LightGroupRuntimeController:
    """Policy/runtime host for a reconciled native HA light-group helper."""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        entities: list[str],
        category: str,
        child_categories: list[str] | None = None,
        feature_config: dict[str, object] | None = None,
    ) -> None:
        """Initialize the non-entity runtime host."""
        self.hass = hass
        self._area_config = area_config
        self._coordinator = coordinator
        self._area_id = area_config.id
        self._area_name = area_config.name
        self._entity_ids = list(entities)
        self.category: str | None = category
        self._child_categories = child_categories or []
        self._child_ids: list[str] | None = None
        self._feature_config = feature_config or {}
        self._listener_registry = ListenerRegistry(logger_name=__name__)
        self.logger = _LOGGER

        self._attr_is_on: bool | None = False
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._last_known_area_states: list[str] = []
        self._last_known_area_states_from_dispatcher = False
        self._listeners_initialized = False
        self._bright_since_monotonic: float | None = None
        self._last_turn_on_monotonic: float | None = None
        self._last_control_activity_monotonic: float | None = None
        self._inside_lux_samples: list[tuple[float, float]] = []

        self._native_control_target_unique_id = build_light_group_helper_surface_unique_id(
            entry_id=area_config.hass_config.entry_id,
            area_id=area_config.id,
            category=category,
        )
        ambient_signal_surface = ambient_rise_signal_surface(
            entry_id=area_config.hass_config.entry_id,
            area_id=area_config.id,
            area_name=area_config.name,
            feature_config=self._feature_config,
        )
        self._ambient_rise_signal_unique_id = (
            ambient_signal_surface.unique_id if ambient_signal_surface is not None else None
        )
        self._attr_unique_id = self._native_control_target_unique_id
        self.__echo_state = CommandEchoState(
            owner_id=self.unique_id,
            controlling=True,
            awaiting_echo=False,
        )

        preset = (
            get_light_group_preset(self.category)
            if self.category and self.category != LightGroupCategory.ALL
            else None
        )
        self.assigned_states = (
            preset_states(self._feature_config, preset) if preset is not None else []
        )
        self.act_on = (
            preset_act_on_modes(self._feature_config, preset)
            if preset is not None
            else []
        )
        self.policy = build_light_control_group_policy(
            assigned_states=self.assigned_states,
            act_on_modes=self.act_on,
            brightness_mode=brightness_mode(self._feature_config),
            bright_min_on_seconds=bright_min_on_seconds(self._feature_config),
            bright_dwell_seconds=bright_dwell_seconds(self._feature_config),
            inside_bright_entity=inside_bright_entity(self._feature_config),
            outside_context_source=outside_context_source(self._feature_config),
            outside_bright_entity=outside_bright_entity(self._feature_config),
            outside_lux_entity=outside_lux_entity(self._feature_config),
            outside_lux_min=outside_lux_min(self._feature_config),
            outside_lux_inside_entity=outside_lux_inside_entity(self._feature_config),
            outside_lux_inside_delta=outside_lux_inside_delta(self._feature_config),
            outside_lux_inside_ratio_min_percent=outside_lux_inside_ratio_min_percent(
                self._feature_config
            ),
            bright_attribution_hold_seconds=bright_attribution_hold_seconds(
                self._feature_config
            ),
            adaptive_require_ambient_rise=adaptive_require_ambient_rise(
                self._feature_config
            ),
            ambient_rise_window_seconds=ambient_rise_window_seconds(
                self._feature_config
            ),
            ambient_rise_min_delta=ambient_rise_min_delta(self._feature_config),
            light_group_entity_id=self._native_control_target_unique_id,
        )
        self._adaptive_lighting_switch_set = adaptive_lighting_switch_set(
            self._feature_config,
            area_id=area_config.id,
            area_name=area_config.name,
            category=category,
            light_entity_ids=entities,
        )
        self._attr_extra_state_attributes.update(
            {
                "lights": self._entity_ids,
                "controlling": self.controlling,
                "brightness_mode": self.policy.policy.brightness_mode,
                "adaptive_lighting": adaptive_lighting_diagnostics(
                    self._feature_config,
                    area_id=area_config.id,
                    area_name=area_config.name,
                    category=category,
                    light_entity_ids=entities,
                ),
            }
        )

    @property
    def name(self) -> str:
        """Return a concise runtime name for logs."""
        return f"{self._area_name} {self.category} light runtime"

    @property
    def unique_id(self) -> str:
        """Return stable runtime owner ID."""
        return self._attr_unique_id

    @property
    def entity_id(self) -> str:
        """Return the native helper entity ID used as the runtime control target."""
        return self._control_target_entity_id()

    @property
    def is_on(self) -> bool | None:
        """Return cached native-helper on/off state."""
        return self.current_control_target_is_on()

    @property
    def controlling(self) -> bool:
        """Return whether MA currently controls this role."""
        return self.__echo_state.controlling

    @property
    def _echo_state(self) -> CommandEchoState:
        """Return command echo state used by policy runtime."""
        return self.__echo_state

    def _set_echo_state(self, state: CommandEchoState) -> None:
        """Update command echo state."""
        self.__echo_state = state
        self._attr_extra_state_attributes["controlling"] = state.controlling

    async def async_get_last_state(self) -> State | None:
        """No HA entity state is restored for non-entity runtime hosts."""
        return None

    async def async_start(self) -> None:
        """Start policy runtime listeners."""
        await setup_group(self)

    def cleanup(self) -> None:
        """Remove runtime listeners."""
        self._listener_registry.cleanup()

    async def _setup_listeners(self) -> None:
        """Set up listeners for area/native-helper state changes."""
        from custom_components.magic_areas.light_groups.runtime import setup_listeners

        setup_listeners(self)

    def track_group_listener(
        self, remove_listener: Callable[[], None], name: str
    ) -> None:
        """Track a runtime listener for setup-entry unload cleanup."""
        self._listener_registry.track(name, remove_listener)

    def async_write_ha_state(self) -> None:
        """Compatibility no-op; runtime diagnostics are not exposed as HA entities."""
        return None

    @callback
    def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle area-state dispatcher events."""
        return handle_area_state_change(self, area_id, states_tuple)

    @callback
    def group_state_changed(self, event: Event[EventStateChangedData]) -> bool:
        """Handle native helper state changes."""
        return handle_group_state_change(self, event)

    def state_change_primary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle primary state changes."""
        return evaluate_state_change(self, states_tuple, is_primary=True)

    def state_change_secondary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle secondary state changes."""
        return evaluate_state_change(self, states_tuple, is_primary=False)

    def _dispatch_light_action(
        self,
        action: LightAction,
        target_entity_ids: tuple[str, ...] | None = None,
    ) -> None:
        """Dispatch canonical light action through shared control execution."""
        target_entity_ids = target_entity_ids or (self._control_target_entity_id(),)
        self.hass.async_create_task(
            execute_control_group_decision(
                self.hass,
                light_action_to_control_group(action, target_entity_ids),
            )
        )

    def light_member_suppression_members(
        self,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return sleep/accent memberships for member-level suppression."""
        sleep_preset = get_light_group_preset(LightGroupCategory.SLEEP)
        accent_preset = get_light_group_preset(LightGroupCategory.ACCENT)
        return (
            self._resolved_role_members(sleep_preset),
            self._resolved_role_members(accent_preset),
        )

    def _resolved_role_members(self, preset: LightGroupPreset | None) -> tuple[str, ...]:
        """Resolve role members from reconciled labels with config fallback."""
        if preset is None:
            return ()
        fallback_entity_ids = preset_members(
            self._feature_config,
            preset,
            available_entities=list(self._entity_ids),
        )
        target = resolve_role_target(
            self.hass,
            area_id=self._area_id,
            domain=LIGHT_DOMAIN,
            role=str(preset.category),
            area_entity_ids=self._entity_ids,
            label_name=LIGHT_GROUP_ROLE_LABELS.get(str(preset.category)),
            fallback_entity_ids=fallback_entity_ids,
            fallback_source=ControlTargetSource.CONFIG_RECONCILIATION,
        )
        return target.target_entity_ids

    def _control_target_entity_id(self) -> str:
        """Return the reconciled native helper target."""
        native_target = resolve_managed_surface_entity_id(
            self.hass,
            er.async_get(self.hass),
            unique_id=self._native_control_target_unique_id,
            entity_domain=LIGHT_DOMAIN,
            config_entry_domain=GROUP_DOMAIN,
        )
        if native_target is None:
            raise RuntimeError(
                f"Managed light helper is not available for {self.name} "
                f"({self._native_control_target_unique_id})"
            )
        return native_target

    def current_control_target_is_on(self) -> bool | None:
        """Return current native helper on/off state when available."""
        try:
            target_entity_id = self._control_target_entity_id()
        except RuntimeError:
            return None
        target_state = self.hass.states.get(target_entity_id)
        if target_state is not None and target_state.state in (STATE_ON, STATE_OFF):
            return target_state.state == STATE_ON
        return None

    def is_control_enabled(self) -> bool:
        """Return whether the Magic Areas light-control switch is enabled."""
        if not self._coordinator.data:
            return True

        entity_id = self._coordinator.data.entity_references.light_control_switch
        if not entity_id:
            return True

        switch_entity = self.hass.states.get(entity_id)
        if not switch_entity:
            return True

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self) -> None:
        """Reset control status."""
        self._reset_control_state()
        self.logger.debug("%s: Control Reset.", self.name)

    def _reset_control_state(self) -> None:
        """Reset command-echo control state."""
        self._set_echo_state(
            CommandEchoState(
                owner_id=self.unique_id,
                controlling=True,
                awaiting_echo=False,
            )
        )


__all__ = ["LightGroupRuntimeController"]
