"""Fan Control switch."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import (
    EntityCategory,
    STATE_OFF,
)
from homeassistant.core import Event, EventStateChangedData, callback

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.controls.policies.fan import (
    build_fan_control_group_policy,
    FanControlGroupPolicy,
    FanPolicySignals,
)
from custom_components.magic_areas.core.config.feature_readers import (
    fan_groups_config,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import (
    ControlGroupContext,
    resolve_area_presence_states,
)
from custom_components.magic_areas.core.aggregates import aggregate_group_id
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import ControlSwitchBase

_LOGGER = logging.getLogger(__name__)


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
        self._last_states = []

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve entity IDs from coordinator snapshot
        entity_refs = self._entity_refs()
        if entity_refs:
            self._fan_group_entity_id = entity_refs.fan_group

        from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN

        self._area_sensor_entity_id = self._resolve_area_state_sensor_entity_id()
        if not self.tracked_entity_id:
            self.tracked_entity_id = self._resolve_entity_id_by_unique_id(
                SENSOR_DOMAIN,
                aggregate_group_id(
                    area_id=self._area_id,
                    device_class=self._tracked_device_class,
                ),
            )
        if not self._fan_group_entity_id:
            self._fan_group_entity_id = self._resolve_primary_group_entity_id(
                policy_id=str(ControlGroupPolicyId.FAN_GROUPS),
                domain=FAN_DOMAIN,
            )
        self._track_area_state_dispatcher(self.area_state_changed)
        self._track_state_change(
            "aggregate_sensor_state_change",
            self.tracked_entity_id,
            self.aggregate_sensor_state_changed,
        )
        self._track_state_change(
            "area_sensor_state_change",
            self._area_sensor_entity_id,
            self._area_sensor_state_changed,
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

        # Read sensor value
        sensor_value = None
        if self.tracked_entity_id:
            sensor_state = self.hass.states.get(self.tracked_entity_id)
            if sensor_state:
                try:
                    sensor_value = float(sensor_state.state)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "%s: Could not parse sensor value from '%s'",
                        self.name,
                        sensor_state.state,
                    )
                    sensor_value = None
            else:
                _LOGGER.warning(
                    "%s: Tracked sensor entity '%s' is not found. Please ensure aggregates are enabled and the selected device class is configured.",
                    self.name,
                    self.tracked_entity_id,
                )

        fan_state = (
            self.hass.states.get(self._fan_group_entity_id)
            if self._fan_group_entity_id
            else None
        )
        context = ControlGroupContext(
            group_id=f"fan_groups_{self._area_id}",
            current_states=tuple(states),
            signals=FanPolicySignals(
                sensor_value=sensor_value,
                fan_group_entity_id=self._fan_group_entity_id,
                fan_group_state=fan_state.state if fan_state else None,
            ),
            is_enabled=self.is_on,
        )
        await self._evaluate_policy(
            policy=self.policy,
            context=context,
            logger=_LOGGER,
        )
