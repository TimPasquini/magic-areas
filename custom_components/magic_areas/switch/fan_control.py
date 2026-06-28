"""Fan Control switch."""

import logging
from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN
from homeassistant.const import (
    EntityCategory,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_call_later

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.controls.policies.fan import (
    build_fan_control_group_policy,
    FanClearBehavior,
    FanControlGroupPolicy,
    FanControllerConfig,
    FanControllerRole,
    FanDetectionMode,
    LEGACY_FAN_SENSOR_KEY,
    FanPolicySignals,
    FanSensorUnavailableBehavior,
)
from custom_components.magic_areas.core.controls.fan_signals import (
    fan_controller_trend_signal_surface,
)
from custom_components.magic_areas.core.managed_surface_registry import (
    resolve_managed_surface_entity_id,
)
from custom_components.magic_areas.features.config.readers import (
    fan_groups_config,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import (
    ControlGroupContext,
    MonotonicDeadlineMap,
    merged_extra_state_attributes,
    resolve_area_presence_states,
)
from custom_components.magic_areas.core.aggregates import resolve_aggregate_entity_id
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from homeassistant.helpers import entity_registry as er
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from custom_components.magic_areas.switch.base import ControlSwitchBase

_LOGGER = logging.getLogger(__name__)
_FAN_ROLE_AREA_STATES: dict[str, str] = {
    FanControllerRole.COOLING.value: AreaStates.HOT.value,
    FanControllerRole.HUMIDITY.value: AreaStates.HUMID.value,
    FanControllerRole.ODOR.value: AreaStates.ODOR.value,
}


class FanControlSwitch(ControlSwitchBase):
    """Switch to enable/disable fan control."""

    feature_id = MagicAreasFeatures.FAN_GROUPS
    _attr_entity_category = EntityCategory.CONFIG

    policy: FanControlGroupPolicy
    tracked_entity_id: str | None
    _tracked_device_class: str
    _last_states: list[str]
    _area_sensor_entity_id: str | None
    _fan_group_entity_id: str | None
    _controller_sensor_entity_ids: tuple[str, ...]
    _controller_trend_signal_unique_ids: dict[str, str]
    _controller_trend_signal_entity_ids: dict[str, str]
    _post_clear_hold_until_monotonic: MonotonicDeadlineMap[str]
    _unavailable_hold_until_monotonic: MonotonicDeadlineMap[str]
    _hold_timer_cancel: Callable[[], None] | None

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Fan control switch."""

        super().__init__(area_config, coordinator)

        feature_config = self.get_feature_config()

        self._tracked_device_class = str(
            fan_groups_config(feature_config).tracked_device_class
        )
        # Entity IDs resolved in async_added_to_hass from coordinator snapshot
        self.tracked_entity_id = None
        self._area_sensor_entity_id = None
        self._fan_group_entity_id = None

        # Build canonical control-group policy from feature configuration.
        self.policy = build_fan_control_group_policy(feature_config)
        self._controller_sensor_entity_ids = tuple(
            sorted(
                {
                    controller.sensor_entity_id
                    for controller in self.policy.controllers
                    if controller.sensor_entity_id
                    and controller.sensor_entity_id != LEGACY_FAN_SENSOR_KEY
                }
            )
        )
        self._controller_trend_signal_unique_ids = {}
        for controller in self.policy.controllers:
            if controller.detection_mode is not FanDetectionMode.THRESHOLD_TREND:
                continue
            signal_surface = fan_controller_trend_signal_surface(
                entry_id=area_config.hass_config.entry_id,
                area_id=area_config.id,
                area_name=area_config.name,
                controller=controller,
            )
            if signal_surface is not None:
                self._controller_trend_signal_unique_ids[controller.controller_id] = (
                    signal_surface.unique_id
                )
        self._controller_trend_signal_entity_ids = {}
        self._post_clear_hold_until_monotonic = MonotonicDeadlineMap()
        self._unavailable_hold_until_monotonic = MonotonicDeadlineMap()
        self._hold_timer_cancel = None
        self._last_states = []

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve entity IDs from coordinator snapshot
        entity_refs = self._entity_refs()
        if entity_refs:
            self._fan_group_entity_id = entity_refs.fan_group

        from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN

        if not self.tracked_entity_id:
            self.tracked_entity_id = resolve_aggregate_entity_id(
                self.hass,
                group_registry=self._coordinator.data.group_registry,
                area_id=self._area_id,
                domain=SENSOR_DOMAIN,
                device_class=self._tracked_device_class,
            )
        if not self._fan_group_entity_id:
            self._fan_group_entity_id = self._resolve_primary_group_entity_id(
                policy_id=str(ControlGroupPolicyId.FAN_GROUPS),
                domain=FAN_DOMAIN,
            )
        self._area_sensor_entity_id = self._track_area_state_with_sensor(
            area_state_handler=self.area_state_changed,
            area_sensor_handler=self._area_sensor_state_changed,
        )
        self._track_state_change(
            "aggregate_sensor_state_change",
            self.tracked_entity_id,
            self.aggregate_sensor_state_changed,
        )
        for index, entity_id in enumerate(self._controller_sensor_entity_ids):
            self._track_state_change(
                f"fan_controller_sensor_state_change_{index}",
                entity_id,
                self.aggregate_sensor_state_changed,
            )
        self._controller_trend_signal_entity_ids = (
            self._resolve_controller_trend_signal_entity_ids()
        )
        for (
            controller_id,
            entity_id,
        ) in self._controller_trend_signal_entity_ids.items():
            self._track_state_change(
                f"fan_controller_trend_signal_state_change_{controller_id}",
                entity_id,
                self.aggregate_sensor_state_changed,
            )

    async def aggregate_sensor_state_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Call update state from track state change event."""

        # Resolve area states from cached dispatcher payload, with sensor fallback.
        current_states = resolve_area_presence_states(
            hass=self.hass,
            area_id=self._area_id,
            cached_states=self._last_states,
        )

        await self.run_logic(current_states)

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        states = self._extract_relevant_area_states(
            area_id,
            states_tuple,
            require_enabled=False,
        )
        if not states:
            return

        _new_states, _lost_states, current_states = states
        self._last_states = current_states
        await self.run_logic(states=current_states)

    @callback
    def _area_sensor_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Ensure clear-state transitions trigger control reevaluation."""
        if not self.is_on:
            return

        new_state = event.data.get("new_state")
        if not new_state:
            return

        if new_state.state != STATE_OFF:
            return

        self.hass.async_create_task(self.run_logic([str(AreaStates.CLEAR)]))

    async def run_logic(self, states: list[str]) -> None:
        """Run fan control logic."""

        if not self.is_on:
            _LOGGER.debug("%s: Control disabled, skipping.", self.name)
            return

        sensor_value = self._read_float_state(
            self.tracked_entity_id,
            missing_log=(
                "%s: Tracked sensor entity '%s' is not found. Please ensure "
                "aggregates are enabled and the selected device class is configured."
            ),
        )
        sensor_values = {
            entity_id: self._read_float_state(
                entity_id,
                missing_log=(
                    "%s: Controller sensor entity '%s' is not found. Please ensure "
                    "the selected sensor exists."
                ),
            )
            for entity_id in self._controller_sensor_entity_ids
        }
        trend_states = {
            controller_id: self._read_trend_signal_state(entity_id)
            for controller_id, entity_id in self._controller_trend_signal_entity_ids.items()
        }
        current_states = resolve_area_presence_states(
            hass=self.hass,
            area_id=self._area_id,
            cached_states=states,
        )
        self._refresh_controller_hold_deadlines(
            current_states=current_states,
            sensor_values=sensor_values,
        )

        fan_state = (
            self.hass.states.get(self._fan_group_entity_id)
            if self._fan_group_entity_id
            else None
        )
        context = ControlGroupContext(
            group_id=f"fan_groups_{self._area_id}",
            current_states=tuple(current_states),
            signals=FanPolicySignals(
                sensor_value=sensor_value,
                fan_group_entity_id=self._fan_group_entity_id,
                fan_group_state=fan_state.state if fan_state else None,
                sensor_values=sensor_values,
                trend_states=trend_states,
                post_clear_hold_controller_ids=tuple(
                    self._active_hold_ids(self._post_clear_hold_until_monotonic)
                ),
                unavailable_hold_controller_ids=tuple(
                    self._active_hold_ids(self._unavailable_hold_until_monotonic)
                ),
            ),
            is_enabled=self.is_on,
        )
        await self._evaluate_policy(
            policy=self.policy,
            context=context,
            logger=_LOGGER,
        )
        self._write_policy_debug_attributes()
        self._publish_fan_runtime_states()
        self._schedule_next_hold_expiry_check()
        if self.platform is not None:
            self.async_write_ha_state()

    def _refresh_controller_hold_deadlines(
        self,
        *,
        current_states: list[str],
        sensor_values: dict[str, float | None],
    ) -> None:
        """Start, keep, or clear per-controller fan hold timers."""
        now = monotonic()
        previously_active = (
            {
                reason.controller_id
                for reason in self.policy.last_evaluation.active_reasons
            }
            if self.policy.last_evaluation is not None
            else set()
        )
        current_state_set = {str(state) for state in current_states}

        for controller in self.policy.controllers:
            controller_id = str(controller.controller_id)
            was_active = controller_id in previously_active
            hold_seconds = max(controller.post_clear_hold_seconds, 0)
            gate_cleared = self._controller_state_gate_cleared(
                controller,
                current_state_set=current_state_set,
            )

            if (
                controller.clear_behavior is FanClearBehavior.POST_CLEAR_HOLD
                and gate_cleared
                and was_active
                and hold_seconds > 0
            ):
                self._post_clear_hold_until_monotonic.setdefault_deadline(
                    controller_id,
                    now + hold_seconds,
                )
            elif not gate_cleared:
                self._post_clear_hold_until_monotonic.discard(controller_id)

            sensor_value = (
                sensor_values.get(controller.sensor_entity_id)
                if controller.sensor_entity_id
                else None
            )
            if (
                controller.sensor_unavailable_behavior
                is FanSensorUnavailableBehavior.HOLD_THEN_CLEAR
                and sensor_value is None
                and was_active
                and hold_seconds > 0
            ):
                self._unavailable_hold_until_monotonic.setdefault_deadline(
                    controller_id,
                    now + hold_seconds,
                )
            elif sensor_value is not None:
                self._unavailable_hold_until_monotonic.discard(controller_id)

        self._drop_expired_holds(now)

    @staticmethod
    def _controller_state_gate_cleared(
        controller: FanControllerConfig,
        *,
        current_state_set: set[str],
    ) -> bool:
        """Return whether the controller's area-state gate is currently cleared."""
        state_gate_met = any(
            state in current_state_set for state in controller.active_states
        )
        return AreaStates.CLEAR in current_state_set or not state_gate_met

    def _active_hold_ids(self, holds: MonotonicDeadlineMap[str]) -> list[str]:
        """Return controller IDs whose hold deadlines have not expired."""
        return list(holds.active_keys(monotonic()))

    def _drop_expired_holds(self, now: float) -> None:
        """Remove expired controller hold deadlines."""
        self._post_clear_hold_until_monotonic.drop_expired(now)
        self._unavailable_hold_until_monotonic.drop_expired(now)

    def _schedule_next_hold_expiry_check(self) -> None:
        """Re-run fan policy when the next fan hold expires."""
        if self._hold_timer_cancel is not None:
            self._hold_timer_cancel()
            self._hold_timer_cancel = None

        now = monotonic()
        delays = tuple(
            delay
            for holds in (
                self._post_clear_hold_until_monotonic,
                self._unavailable_hold_until_monotonic,
            )
            if (delay := holds.next_delay(now)) is not None
        )
        if not delays:
            return

        self._hold_timer_cancel = async_call_later(
            self.hass,
            min(delays),
            self._hold_expiry_check,
        )

    async def _hold_expiry_check(self, _now: object) -> None:
        """Reevaluate fan policy after a hold timer expires."""
        self._hold_timer_cancel = None
        states = resolve_area_presence_states(
            hass=self.hass,
            area_id=self._area_id,
            cached_states=self._last_states,
        )
        await self.run_logic(states)

    def _resolve_controller_trend_signal_entity_ids(self) -> dict[str, str]:
        """Resolve managed Trend helper entity IDs for threshold+trend controllers."""
        entity_registry = er.async_get(self.hass)
        resolved: dict[str, str] = {}
        for (
            controller_id,
            unique_id,
        ) in self._controller_trend_signal_unique_ids.items():
            entity_id = resolve_managed_surface_entity_id(
                self.hass,
                entity_registry,
                unique_id=unique_id,
                entity_domain=BINARY_SENSOR_DOMAIN,
                config_entry_domain=TREND_DOMAIN,
            )
            if entity_id is not None:
                resolved[controller_id] = entity_id
        return resolved

    def _read_trend_signal_state(self, entity_id: str) -> bool | None:
        """Read a native Trend helper binary state."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None
        return state.state == STATE_ON

    def _write_policy_debug_attributes(self) -> None:
        """Expose fan controller evaluation details for troubleshooting."""
        evaluation = self.policy.last_evaluation
        if evaluation is None:
            return

        self._attr_extra_state_attributes = merged_extra_state_attributes(
            getattr(self, "_attr_extra_state_attributes", None),
            {
                "active_fan_reasons": [
                    reason.controller_id for reason in evaluation.active_reasons
                ],
                "suppressed_fan_reasons": [
                    reason.controller_id for reason in evaluation.suppressed_reasons
                ],
                "inactive_fan_reasons": [
                    reason.controller_id for reason in evaluation.inactive_reasons
                ],
                "target_fan_entities": list(evaluation.target_fan_entity_ids),
                "post_clear_hold_fan_reasons": self._active_hold_ids(
                    self._post_clear_hold_until_monotonic
                ),
                "unavailable_hold_fan_reasons": self._active_hold_ids(
                    self._unavailable_hold_until_monotonic
                ),
            },
        )

    def _publish_fan_runtime_states(self) -> None:
        """Publish active fan reason states to the area-state entity."""
        evaluation = self.policy.last_evaluation
        if evaluation is None:
            return

        states = [
            state
            for reason in evaluation.active_reasons
            if (state := _FAN_ROLE_AREA_STATES.get(reason.controller_id))
        ]
        dispatcher_send(
            self.hass,
            MagicAreasEvents.AREA_RUNTIME_STATES_CHANGED,
            self._area_id,
            "fan_groups",
            states,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up fan hold timer on entity removal."""
        if self._hold_timer_cancel is not None:
            self._hold_timer_cancel()
            self._hold_timer_cancel = None
        await super().async_will_remove_from_hass()
