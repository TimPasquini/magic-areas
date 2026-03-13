"""Base classes for switch."""

from collections.abc import Callable
from logging import Logger
from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_ON
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.entity import MagicEntity
from custom_components.magic_areas.const import ONE_MINUTE
from custom_components.magic_areas.core.controls import (
    evaluate_and_execute_control_group_policy,
    execute_control_group_decision,
    resolve_group_entity_id_by_metadata,
    resolve_group_member_entity_id_by_metadata,
)
from custom_components.magic_areas.core.runtime_model import GroupMetadataKey, GroupRole
from custom_components.magic_areas.core.runtime_model import build_presence_tracking_unique_id
from custom_components.magic_areas.core.listener_registry import ListenerRegistry
from custom_components.magic_areas.enums import MagicAreasEvents

if TYPE_CHECKING:
    from homeassistant.core import Event, EventStateChangedData
    from homeassistant.helpers.entity_registry import EntityRegistry

    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.core.controls import (
        ControlGroupPolicy,
        ControlGroupContext,
        ControlGroupDecision,
    )
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.core.runtime_model import (
        EntityReferences,
        GroupRegistryView,
    )

type AreaStatesTuple = tuple[list[str], list[str], list[str]]
type AreaStateEventHandler = Callable[[str, AreaStatesTuple], object]
type StateChangeEventHandler = Callable[[Event[EventStateChangedData]], object]


class SwitchBase(MagicEntity, SwitchEntity):
    """The base class for all the switches."""

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the base switch bits, basic just a mixin for the two types."""
        MagicEntity.__init__(self, area_config, coordinator, domain=SWITCH_DOMAIN)
        SwitchEntity.__init__(self)
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_should_poll = False
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Restore state
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn on presence hold."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn off presence hold."""
        self._attr_is_on = False
        self.async_write_ha_state()


class ResettableSwitchBase(SwitchBase):
    """Control the presence/state from being changed for the device."""

    timeout: int
    _listener_registry: ListenerRegistry

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator", timeout: int = 0
    ) -> None:
        """Initialize the switch."""
        super().__init__(area_config, coordinator)

        self.timeout = timeout
        self._timeout_callback: Callable[[], None] | None = None
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

        self._listener_registry.track("timer_cleanup", self._clear_timers)

    def _clear_timers(self, _: object = None) -> None:
        """Remove the timer on entity removal."""
        if self._timeout_callback:
            self._timeout_callback()

    async def _timeout_turn_off(self, next_interval: object) -> None:
        """Turn off the presence hold after the timeout."""
        if self.is_on:
            await self.async_turn_off()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn on presence hold."""
        self._attr_is_on = True
        self.async_write_ha_state()

        if self.timeout and not self._timeout_callback:
            self._timeout_callback = async_call_later(
                self.hass, self.timeout * ONE_MINUTE, self._timeout_turn_off
            )

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn off presence hold."""
        self._attr_is_on = False
        self.async_write_ha_state()

        if self._timeout_callback:
            self._timeout_callback()
            self._timeout_callback = None

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()


class ControlSwitchBase(SwitchBase):
    """Base class for control switches that react to area state changes."""

    _listener_registry: ListenerRegistry

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize control switch scaffolding."""
        super().__init__(area_config, coordinator)
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    def _track_area_state_dispatcher(self, handler: AreaStateEventHandler) -> None:
        """Track area-state dispatcher listener."""
        self._listener_registry.track(
            "area_state_dispatcher",
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, handler
            ),
        )

    def _track_state_change(
        self,
        key: str,
        entity_id: str | None,
        handler: StateChangeEventHandler,
    ) -> None:
        """Track state-change listener for a single entity id."""
        if not entity_id:
            return
        self._listener_registry.track(
            key,
            async_track_state_change_event(self.hass, [entity_id], handler),
        )

    def _extract_relevant_area_states(
        self,
        area_id: str,
        states_tuple: AreaStatesTuple,
        *,
        require_enabled: bool = True,
    ) -> tuple[list[str], list[str], list[str]] | None:
        """Return event states when the event should be processed."""
        if require_enabled and not self.is_on:
            self.logger.debug("%s: Control disabled. Skipping.", self.name)
            return None

        if area_id != self._area_id:
            self.logger.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self._area_id,
            )
            return None

        new_states, lost_states, current_states = states_tuple
        if not new_states and not lost_states:
            return None
        return new_states, lost_states, current_states

    async def _execute_decision(
        self, decision: "ControlGroupDecision", *, blocking: bool = False
    ) -> None:
        """Execute a control-group decision."""
        await execute_control_group_decision(self.hass, decision, blocking=blocking)

    async def _evaluate_policy(
        self,
        *,
        policy: "ControlGroupPolicy",
        context: "ControlGroupContext",
        logger: Logger | None = None,
        blocking: bool = False,
    ) -> "ControlGroupDecision":
        """Evaluate policy and execute the resulting control-group decision."""
        executor = (
            (lambda decision: self._execute_decision(decision, blocking=True))
            if blocking
            else self._execute_decision
        )
        return await evaluate_and_execute_control_group_policy(
            policy=policy,
            context=context,
            execute_decision=executor,
            logger=logger or self.logger,
            actor_name=str(self.name),
        )

    def _entity_refs(self) -> "EntityReferences | None":
        """Return coordinator entity references when available."""
        if self._coordinator.data:
            return self._coordinator.data.entity_references
        return None

    def _entity_registry(self) -> "EntityRegistry":
        """Return Home Assistant entity registry."""
        return er.async_get(self.hass)

    def _group_registry(self) -> "GroupRegistryView | None":
        """Return active group registry from coordinator snapshot."""
        if self._coordinator.data:
            return self._coordinator.data.group_registry
        return None

    def _resolve_entity_id_by_unique_id(self, domain: str, unique_id: str) -> str | None:
        """Resolve entity_id for the integration domain by unique_id."""
        from custom_components.magic_areas.const import DOMAIN

        return self._entity_registry().async_get_entity_id(domain, DOMAIN, unique_id)

    def _resolve_area_state_sensor_entity_id(self) -> str | None:
        """Resolve area-state sensor entity id from snapshot refs or unique-id fallback."""
        entity_refs = self._entity_refs()
        if entity_refs and entity_refs.area_state_sensor:
            return entity_refs.area_state_sensor

        from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN

        return self._resolve_entity_id_by_unique_id(
            BS_DOMAIN,
            build_presence_tracking_unique_id(area_id=self._area_id),
        )

    def _resolve_primary_group_entity_id(self, *, policy_id: str, domain: str) -> str | None:
        """Resolve the primary control-group entity for the area/policy/domain."""
        group_registry = self._group_registry()
        if group_registry is None:
            return None
        return resolve_group_entity_id_by_metadata(
            self.hass,
            group_registry=group_registry,
            area_id=self._area_id,
            policy_id=policy_id,
            domain=domain,
            metadata_key=str(GroupMetadataKey.ROLE),
            metadata_value=str(GroupRole.PRIMARY),
        )

    def _resolve_primary_group_member_entity_id(self, *, policy_id: str) -> str | None:
        """Resolve the first member from the primary control group for a policy."""
        group_registry = self._group_registry()
        if group_registry is None:
            return None
        return resolve_group_member_entity_id_by_metadata(
            group_registry=group_registry,
            area_id=self._area_id,
            policy_id=policy_id,
            metadata_key=str(GroupMetadataKey.ROLE),
            metadata_value=str(GroupRole.PRIMARY),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()
