"""Climate control feature switch."""

import logging
from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory, STATE_OFF, STATE_ON
from homeassistant.core import Event, callback
from homeassistant.helpers.event import EventStateChangedData

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.controls.policies.climate import (
    build_climate_control_group_policy,
    build_preset_policy,
    ClimatePolicySignals,
    ClimateControlGroupPolicy,
    ClimatePresetPolicy,
)
from custom_components.magic_areas.features.config.readers import (
    climate_control_config,
)
from custom_components.magic_areas.core.controls import ControlGroupContext
from custom_components.magic_areas.core.runtime_model import ControlGroupPolicyId
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import ControlSwitchBase

_LOGGER = logging.getLogger(__name__)
_EXPECTED_CONTROL_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


class ClimateControlSwitch(ControlSwitchBase):
    """Switch to enable/disable climate control."""

    feature_id = MagicAreasFeatures.CLIMATE_CONTROL
    _attr_entity_category = EntityCategory.CONFIG

    policy: ClimateControlGroupPolicy
    _preset_policy: ClimatePresetPolicy
    climate_entity_id: str | None
    _area_sensor_entity_id: str | None
    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Climate control switch."""

        super().__init__(area_config, coordinator)

        feature_config = self.get_feature_config()
        self.climate_entity_id = climate_control_config(feature_config).entity_id

        # Build canonical policy and retain preset map for direct state hooks.
        self._preset_policy = build_preset_policy(feature_config)
        self.policy = build_climate_control_group_policy(feature_config)
        # Entity ID resolved in async_added_to_hass from coordinator snapshot
        self._area_sensor_entity_id = None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        if not self.climate_entity_id:
            self.climate_entity_id = self._resolve_primary_group_member_entity_id(
                policy_id=str(ControlGroupPolicyId.CLIMATE_CONTROL),
            )
        # Resolve area sensor entity ID from coordinator snapshot or entity registry
        self._area_sensor_entity_id = self._resolve_area_state_sensor_entity_id()

        self._track_area_state_dispatcher(self.area_state_changed)
        self._track_state_change(
            "area_sensor_state_change",
            self._area_sensor_entity_id,
            self._area_sensor_state_changed,
        )

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        states = self._extract_relevant_area_states(
            area_id,
            states_tuple,
            require_enabled=True,
        )
        if not states:
            return

        new_states, lost_states, current_states = states
        await self._evaluate_policy(
            policy=self.policy,
            context=ControlGroupContext(
                group_id=f"climate_control_{self._area_id}",
                new_states=tuple(new_states),
                lost_states=tuple(lost_states),
                current_states=tuple(current_states),
                signals=ClimatePolicySignals(
                    climate_entity_id=self.climate_entity_id,
                    preset_name=None,
                ),
                is_enabled=bool(self.is_on),
            ),
            logger=_LOGGER,
            blocking=True,
        )

    @callback
    def _area_sensor_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle area sensor state change to keep presets in sync."""
        if not self.is_on:
            return

        new_state = event.data.get("new_state")
        if not new_state:
            return

        if (
            new_state.state == STATE_OFF
            and self._preset_policy.preset_map[AreaStates.CLEAR]
        ):
            self.hass.async_create_task(self.apply_preset(AreaStates.CLEAR))
            return

        if (
            new_state.state == STATE_ON
            and self._preset_policy.preset_map[AreaStates.OCCUPIED]
        ):
            self.hass.async_create_task(self.apply_preset(AreaStates.OCCUPIED))

    async def apply_preset(self, state_name: str) -> None:
        """Set climate entity to preset for given state."""
        selected_preset = self._preset_policy.preset_map.get(state_name)
        if selected_preset:
            await self.apply_preset_by_name(selected_preset)

    async def apply_preset_by_name(self, preset_name: str) -> None:
        """Set climate entity to given preset by name."""
        if not self.climate_entity_id:
            self.logger.debug(
                "%s: No climate entity resolved, cannot apply preset.", self.name
            )
            return
        try:
            await self._evaluate_policy(
                policy=self.policy,
                context=ControlGroupContext(
                    group_id=f"climate_control_{self._area_id}",
                    current_states=(),
                    signals=ClimatePolicySignals(
                        climate_entity_id=self.climate_entity_id,
                        preset_name=preset_name,
                    ),
                    is_enabled=bool(self.is_on),
                ),
                logger=_LOGGER,
                blocking=True,
            )
        except _EXPECTED_CONTROL_ERRORS as exc:
            self.logger.exception("%s: Error applying preset: %s", self.name, str(exc))
