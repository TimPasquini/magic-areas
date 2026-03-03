"""Light group entity implementations for Magic Areas."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    STATE_ON,
)
from homeassistant.core import Event, callback
from homeassistant.helpers import entity_registry as entity_registry_module
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)

from custom_components.magic_areas.const import DOMAIN, EVENT_MAGICAREAS_AREA_STATE_CHANGED
from custom_components.magic_areas.core.command_echo import (
    CommandEchoState,
    CommandEchoTracker,
)
from custom_components.magic_areas.core.control_group_executor import (
    execute_control_group_decision,
)
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_ids_by_metadata,
)
from custom_components.magic_areas.light_groups.policy import (
    LightAction,
    build_light_control_group_policy,
    light_action_to_control_group,
    reset_control_state,
)
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups.actions import forward_turn_on
from custom_components.magic_areas.light_groups import events as group_events
from custom_components.magic_areas.light_groups.config import (
    DEFAULT_LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
    LIGHT_GROUP_STATES,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class MagicLightGroup(MagicGroupEntity, LightGroup):
    """Magic Light Group for Meta-areas."""

    feature_id = MagicAreasFeatures.LIGHT_GROUPS

    def __init__(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        entities: list[str],
        translation_key: str | None = None,
    ) -> None:
        """Initialize parent class and state."""
        MagicGroupEntity.__init__(
            self,
            area_config,
            coordinator,
            domain=LIGHT_DOMAIN,
            member_entity_ids=entities,
            translation_key=translation_key,
        )
        LightGroup.__init__(
            self,
            name="",
            unique_id=self.unique_id,
            entity_ids=self.member_entity_ids,
            mode=False,
        )
        delattr(self, "_attr_name")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Forward the turn_on command to all lights in the light group."""
        await forward_turn_on(self.hass, self._area_name, self._entity_ids, **kwargs)


class AreaLightGroup(MagicLightGroup):
    """Magic Light Group."""

    def __init__(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        entities: list[str],
        category: str | None = None,
        child_categories: list[str] | None = None,
        feature_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize light group."""
        MagicLightGroup.__init__(
            self, area_config, coordinator, entities, translation_key=category
        )

        self._child_categories = child_categories or []
        self._child_ids: list[str] | None = None
        self._feature_config = feature_config or {}

        self.category = category
        self.assigned_states: list[str] = []
        self.act_on: list[str] = []

        self._echo_tracker = CommandEchoTracker()
        self._echo_tracker.set_state(
            CommandEchoState(
                owner_id=self.unique_id,
                controlling=True,
                awaiting_echo=False,
            )
        )

        # Initialize area states cache (will be updated by _setup_listeners)
        self._last_known_area_states: list[str] = []
        self._listeners_initialized = False

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        if self.category and self.category != LightGroupCategory.ALL:
            self._icon = LIGHT_GROUP_ICONS.get(self.category, LIGHT_GROUP_DEFAULT_ICON)

        # Get assigned states
        if self.category and self.category != LightGroupCategory.ALL:
            self.assigned_states = self._feature_config.get(
                LIGHT_GROUP_STATES[self.category], []
            )
            self.act_on = self._feature_config.get(
                LIGHT_GROUP_ACT_ON[self.category], DEFAULT_LIGHT_GROUP_ACT_ON
            )

        # Build canonical control-group policy adapter.
        self.policy = build_light_control_group_policy(
            assigned_states=self.assigned_states,
            act_on_modes=self.act_on,
            light_group_entity_id=self.entity_id,
        )

        self._attr_extra_state_attributes = dict(
            self._attr_extra_state_attributes or {}
        )

        # Add static attributes
        self._attr_extra_state_attributes["lights"] = self._entity_ids
        self._attr_extra_state_attributes["controlling"] = self.controlling

        self.logger.debug(
            "%s: Light group (%s) created with entities: %s",
            self._area_name,
            category,
            str(self._entity_ids),
        )

    @property
    def icon(self) -> str:
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def controlling(self) -> bool:
        """Return whether this group is currently controlling."""
        return self._echo_tracker.state.controlling

    @property
    def _echo_state(self) -> CommandEchoState:
        """Internal echo state used by light group runtime."""
        return self._echo_tracker.state

    def _set_echo_state(self, state: CommandEchoState) -> None:
        """Update echo state and sync attributes."""
        self._echo_tracker.set_state(state)
        self._attr_extra_state_attributes["controlling"] = state.controlling

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = dict(self._attr_extra_state_attributes or {})
        attrs["lights"] = self._entity_ids
        attrs["controlling"] = self.controlling
        if self._child_ids is not None:
            attrs["child_ids"] = self._child_ids
        return attrs

    async def _async_setup_group(self) -> None:
        """Set up light group - called by MagicGroupEntity lifecycle."""
        self._attr_extra_state_attributes = dict(
            self._attr_extra_state_attributes or {}
        )

        # Resolve child_ids from entity registry (category groups are registered before ALL group)
        if self.category == LightGroupCategory.ALL and self._child_categories:
            resolved_ids = []
            category_entity_ids = resolve_group_entity_ids_by_metadata(
                self.hass,
                area_id=self._area_id,
                policy_id="light_groups",
                domain=LIGHT_DOMAIN,
                metadata_key="category",
            )
            for category in self._child_categories:
                entity_id = category_entity_ids.get(category)
                if entity_id:
                    resolved_ids.append(entity_id)
            if not resolved_ids:
                from homeassistant.helpers import entity_registry as er

                registry = er.async_get(self.hass)
                for category in self._child_categories:
                    child_uid = f"light_groups_{self._area_id}_{category}"
                    child_entity_id = registry.async_get_entity_id(
                        LIGHT_DOMAIN, DOMAIN, child_uid
                    )
                    if child_entity_id:
                        resolved_ids.append(child_entity_id)
            self._child_ids = resolved_ids or None
            self._attr_extra_state_attributes["child_ids"] = self._child_ids

        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(
                "%s: State restored [state=%s]", self.name, last_state.state
            )
            self._attr_is_on = last_state.state == STATE_ON

            if "controlling" in last_state.attributes:
                controlling = last_state.attributes["controlling"]
                self._set_echo_state(
                    CommandEchoState(
                        owner_id=self.unique_id,
                        controlling=controlling,
                        awaiting_echo=False,
                    )
                )
        else:
            self._attr_is_on = False

        self._attr_extra_state_attributes["lights"] = self._entity_ids
        self._attr_extra_state_attributes["controlling"] = self.controlling

        # Setup state change listeners
        await self._setup_listeners()

    async def _setup_listeners(self, _: Any = None) -> None:
        """Set up listeners for area state change."""
        if self._listeners_initialized:
            return

        # Initialize cache from live HA state (read from presence binary sensor)
        entity_registry = entity_registry_module.async_get(self.hass)
        presence_entity_id = entity_registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"presence_tracking_{self._area_id}_area_state",
        )
        if presence_entity_id:
            state = self.hass.states.get(presence_entity_id)
            if state and "states" in state.attributes:
                self._last_known_area_states = [
                    str(s.value) if isinstance(s, Enum) else str(s)
                    for s in state.attributes["states"]
                ]
            else:
                self._last_known_area_states = []
        else:
            self._last_known_area_states = []
        self.track_group_listener(
            async_dispatcher_connect(
                self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
            ),
            "area_state_dispatcher",
        )
        self.track_group_listener(
            async_track_state_change_event(
                self.hass,
                [
                    self.entity_id,
                ],
                self.group_state_changed,
            ),
            "group_state_change",
        )
        self._listeners_initialized = True

    # State Change Handling

    @callback
    def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle area state change event."""
        return group_events.area_state_changed(self, area_id, states_tuple)

    def state_change_primary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle primary state change."""
        return group_events.state_change_primary(self, states_tuple)

    def state_change_secondary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle secondary state change."""
        return group_events.state_change_secondary(self, states_tuple)

    # Light Handling

    def _turn_on(self) -> bool:
        """Turn on light if it's not already on and if we're controlling it."""
        if not self._echo_state.controlling:
            return False

        if self.is_on:
            return False

        self._set_echo_state(self._echo_state.command_issued(self.unique_id))

        self.hass.async_create_task(
            execute_control_group_decision(
                self.hass,
                light_action_to_control_group(LightAction.TURN_ON, self.entity_id),
            )
        )

        return True

    def _turn_off(self) -> bool:
        """Turn off light if it's not already off, and we're controlling it."""
        if not self._echo_state.controlling:
            return False

        if not self.is_on:
            return False

        self.hass.async_create_task(
            execute_control_group_decision(
                self.hass,
                light_action_to_control_group(LightAction.TURN_OFF, self.entity_id),
            )
        )

        return True

    # Control Release

    def is_control_enabled(self) -> bool:
        """Check if light control is enabled by checking light control switch state."""
        # Resolve light control switch from entity references
        if not self._coordinator.data:
            return True  # Default to enabled if coordinator data unavailable

        entity_refs = self._coordinator.data.entity_references
        entity_id = entity_refs.light_control_switch

        if not entity_id:
            return True  # Default to enabled if switch not found

        switch_entity = self.hass.states.get(entity_id)

        if not switch_entity:
            return True

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self) -> None:
        """Reset control status."""
        self._set_echo_state(reset_control_state())
        self.schedule_update_ha_state()
        self.logger.debug("%s: Control Reset.", self.name)

    def is_child_controllable(self, entity_id: str) -> bool:
        """Check if child entity is controllable."""
        return group_events.is_child_controllable(self.hass, entity_id)

    def handle_group_state_change_primary(self) -> None:
        """Handle group state change for primary area state events."""
        group_events.handle_group_state_change_primary(self)

    def handle_group_state_change_secondary(self) -> None:
        """Handle group state change for secondary area state events."""
        group_events.handle_group_state_change_secondary(self)

    @callback
    def group_state_changed(self, event: Event[EventStateChangedData]) -> bool:
        """Handle group state change events."""
        return group_events.group_state_changed(self, event)


__all__ = ["MagicLightGroup", "AreaLightGroup"]
