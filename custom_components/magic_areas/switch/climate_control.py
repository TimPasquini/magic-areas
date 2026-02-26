"""Climate control feature switch."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN

from homeassistant.const import ATTR_ENTITY_ID, EntityCategory, STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.config_keys import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
)
from custom_components.magic_areas.core.climate_control import (
    build_preset_policy,
    ClimatePresetPolicy,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import SwitchBase

_LOGGER = logging.getLogger(__name__)


class ClimateControlSwitch(SwitchBase):
    """Switch to enable/disable climate control."""

    feature_id = MagicAreasFeatures.CLIMATE_CONTROL
    _attr_entity_category = EntityCategory.CONFIG

    policy: ClimatePresetPolicy
    climate_entity_id: str | None
    _area_sensor_entity_id: str | None
    _listener_registry: ListenerRegistry

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Climate control switch."""

        SwitchBase.__init__(self, area_config, coordinator)

        feature_config = self.get_feature_config()
        self.climate_entity_id = feature_config.get(
            CONF_CLIMATE_CONTROL_ENTITY_ID, None
        )

        if not self.climate_entity_id:
            raise ValueError("Climate entity not set")

        # Build policy from feature configuration
        self.policy = build_preset_policy(feature_config)
        # Entity ID resolved in async_added_to_hass from coordinator snapshot
        self._area_sensor_entity_id = None
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve area sensor entity ID from coordinator snapshot or entity registry
        if self._coordinator.data:
            self._area_sensor_entity_id = (
                self._coordinator.data.entity_references.area_state_sensor
            )
        if not self._area_sensor_entity_id:
            from homeassistant.helpers import entity_registry as er
            from custom_components.magic_areas.const import DOMAIN
            from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN

            self._area_sensor_entity_id = er.async_get(self.hass).async_get_entity_id(
                BS_DOMAIN, DOMAIN, f"presence_tracking_{self._area_id}_area_state"
            )
        if not self._area_sensor_entity_id:
            # Fallback to the default entity_id pattern if registry lookup is unavailable.
            self._area_sensor_entity_id = (
                f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{self._area_slug}_area_state"
            )

        self._listener_registry.track(
            "area_state_dispatcher",
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self.area_state_changed
            ),
        )
        if self._area_sensor_entity_id:
            self._listener_registry.track(
                "area_sensor_state_change",
                async_track_state_change_event(
                    self.hass,
                    [self._area_sensor_entity_id],
                    self._area_sensor_state_changed,
                ),
            )

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        if not self.is_on:
            self.logger.debug("%s: Control disabled. Skipping.", self.name)
            return

        if area_id != self._area_id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self._area_id,
            )
            return

        new_states, lost_states, current_states = states_tuple

        if not new_states and not lost_states:
            return

        # Use policy to determine which preset to apply
        selected_preset = self.policy.select_preset_for_state_change(
            new_states, current_states
        )
        if selected_preset:
            await self.apply_preset_by_name(selected_preset)

    @callback
    def _area_sensor_state_changed(self, event: Any) -> None:
        """Handle area sensor state change to keep presets in sync."""
        if not self.is_on:
            return

        new_state = event.data.get("new_state")
        if not new_state:
            return

        if new_state.state == STATE_OFF and self.policy.preset_map[AreaStates.CLEAR]:
            self.hass.async_create_task(self.apply_preset(AreaStates.CLEAR))
            return

        if new_state.state == STATE_ON and self.policy.preset_map[AreaStates.OCCUPIED]:
            self.hass.async_create_task(self.apply_preset(AreaStates.OCCUPIED))

    async def apply_preset(self, state_name: str) -> None:
        """Set climate entity to preset for given state."""
        selected_preset = self.policy.preset_map.get(state_name)
        if selected_preset:
            await self.apply_preset_by_name(selected_preset)

    async def apply_preset_by_name(self, preset_name: str) -> None:
        """Set climate entity to given preset by name."""
        try:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_PRESET_MODE,
                {
                    ATTR_ENTITY_ID: self.climate_entity_id,
                    ATTR_PRESET_MODE: preset_name,
                },
                blocking=True,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            self.logger.error("%s: Error applying preset: %s", self.name, str(e))

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()
