"""Light group entity implementations for Magic Areas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.group.light import FORWARDED_ATTRIBUTES, LightGroup
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_ON
from homeassistant.core import Context, Event, State, callback
from homeassistant.helpers.event import EventStateChangedData
from custom_components.magic_areas.light_groups.policy import (
    CommandEchoState,
)
from custom_components.magic_areas.core.controls import (
    execute_control_group_decision,
)
from custom_components.magic_areas.light_groups.policy import (
    LightAction,
    build_light_control_group_policy,
    light_action_to_control_group,
)
from custom_components.magic_areas.light_groups.runtime import (
    evaluate_state_change,
    handle_area_state_change,
    handle_group_state_change,
    restore_group_state,
    setup_group,
    setup_listeners,
)
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups.config import (
    LIGHT_GROUP_DEFAULT_ICON,
    get_light_group_preset,
    preset_act_on_modes,
    preset_states,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
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

    async def async_turn_on(self, **kwargs: object) -> None:
        """Forward the turn_on command to all lights in the light group."""
        active_lights = self._get_active_lights()
        data = {
            key: value
            for key, value in kwargs.items()
            if key in FORWARDED_ATTRIBUTES
        }
        data[ATTR_ENTITY_ID] = active_lights or self._entity_ids
        context = kwargs.get("context")
        await self.hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            data,
            blocking=True,
            context=context if isinstance(context, Context) else None,
        )

    def _get_active_lights(self) -> list[str]:
        """Return lights in this group that are currently on."""
        active_lights: list[str] = []
        for entity_id in self._entity_ids:
            light_state = self.hass.states.get(entity_id)
            if light_state and light_state.state == STATE_ON:
                active_lights.append(entity_id)
        return active_lights


class AreaLightGroup(MagicLightGroup):
    """Magic Light Group."""

    def __init__(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        entities: list[str],
        category: str | None = None,
        child_categories: list[str] | None = None,
        feature_config: dict[str, object] | None = None,
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

        self.__echo_state = CommandEchoState(
            owner_id=self.unique_id,
            controlling=True,
            awaiting_echo=False,
        )

        # Initialize area states cache (will be updated by _setup_listeners)
        self._last_known_area_states: list[str] = []
        self._listeners_initialized = False

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        preset = (
            get_light_group_preset(self.category)
            if self.category and self.category != LightGroupCategory.ALL
            else None
        )
        if preset is not None:
            self._icon = preset.icon

        # Get assigned states
        if preset is not None:
            self.assigned_states = preset_states(self._feature_config, preset)
            self.act_on = preset_act_on_modes(self._feature_config, preset)

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
        return self.__echo_state.controlling

    @property
    def _echo_state(self) -> CommandEchoState:
        """Internal echo state used by light group runtime."""
        return self.__echo_state

    def _set_echo_state(self, state: CommandEchoState) -> None:
        """Update echo state and sync attributes."""
        self.__echo_state = state
        self._attr_extra_state_attributes["controlling"] = state.controlling

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        attrs = dict(self._attr_extra_state_attributes or {})
        attrs["lights"] = self._entity_ids
        attrs["controlling"] = self.controlling
        if self._child_ids is not None:
            attrs["child_ids"] = self._child_ids
        return attrs

    def _restore_group_state(self, last_state: State | None) -> None:
        """Restore basic on/off + control state from last HA state object."""
        restore_group_state(self, last_state)

    async def _async_setup_group(self) -> None:
        """Set up light group - called by MagicGroupEntity lifecycle."""
        await setup_group(self)

    async def _setup_listeners(self) -> None:
        """Set up listeners for area state change."""
        setup_listeners(self)

    # State Change Handling

    @callback
    def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle area state change event."""
        return handle_area_state_change(
            self,
            area_id,
            states_tuple,
        )

    def state_change_primary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle primary state change."""
        return evaluate_state_change(self, states_tuple, is_primary=True)

    def state_change_secondary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle secondary state change."""
        return evaluate_state_change(self, states_tuple, is_primary=False)

    # Light Handling

    def _dispatch_light_action(self, action: LightAction) -> None:
        """Dispatch canonical light action through shared control execution."""
        self.hass.async_create_task(
            execute_control_group_decision(
                self.hass,
                light_action_to_control_group(action, self.entity_id),
            )
        )

    # Control Release

    def is_control_enabled(self) -> bool:
        """Check if light control is enabled by checking light control switch state."""
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
        self.async_write_ha_state()
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

    @callback
    def group_state_changed(self, event: Event[EventStateChangedData]) -> bool:
        """Handle group state change events."""
        return handle_group_state_change(self, event)


__all__ = ["MagicLightGroup", "AreaLightGroup"]
