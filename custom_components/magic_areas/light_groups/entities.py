"""Light group entity implementations for Magic Areas."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.core import Event, callback
from homeassistant.helpers.event import EventStateChangedData

from custom_components.magic_areas.core.command_echo import (
    CommandEchoState,
    CommandEchoTracker,
)
from custom_components.magic_areas.light_groups.policy import (
    build_light_control_group_policy,
    reset_control_state,
)
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups.actions import (
    execute_group_turn_off,
    execute_group_turn_on,
    forward_turn_on,
)
from custom_components.magic_areas.light_groups import events as group_events
from custom_components.magic_areas.light_groups.runtime import (
    is_group_control_enabled,
    resolve_child_group_ids,
    restore_group_state,
)
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
            self._child_ids = resolve_child_group_ids(
                self.hass,
                area_id=self._area_id,
                child_categories=self._child_categories,
            )
            self._attr_extra_state_attributes["child_ids"] = self._child_ids

        # Get last state
        last_state = await self.async_get_last_state()
        restore_group_state(self, last_state)

        self._attr_extra_state_attributes["lights"] = self._entity_ids
        self._attr_extra_state_attributes["controlling"] = self.controlling

        # Setup state change listeners
        await self._setup_listeners()

    async def _setup_listeners(self, _: Any = None) -> None:
        """Set up listeners for area state change."""
        if self._listeners_initialized:
            return

        group_events.initialize_last_known_states(self)
        group_events.register_group_listeners(self)

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
        return execute_group_turn_on(self)

    def _turn_off(self) -> bool:
        """Turn off light if it's not already off, and we're controlling it."""
        return execute_group_turn_off(self)

    # Control Release

    def is_control_enabled(self) -> bool:
        """Check if light control is enabled by checking light control switch state."""
        return is_group_control_enabled(self)

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
