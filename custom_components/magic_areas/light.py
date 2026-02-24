"""Platform file for Magic Area's light entities."""

import logging
from enum import Enum
from typing import Any, TYPE_CHECKING

from homeassistant.components.group.light import FORWARDED_ATTRIBUTES, LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as entity_registry_module
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)

from custom_components.magic_areas.base.entities import MagicGroupEntity

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries
from custom_components.magic_areas.config_keys import (
    EMPTY_STRING,
)
from custom_components.magic_areas.const import (
    DOMAIN,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
)
from custom_components.magic_areas.core.light_control import (
    build_light_group_policy,
    LightAction,
)
from custom_components.magic_areas.light_groups import (
    DEFAULT_LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_CATEGORIES,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
    LIGHT_GROUP_STATES,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoLightGroups,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area light config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping light setup; coordinator data unavailable")
        return
    area_config = data.area_config
    coordinator = runtime_data.coordinator
    entities_by_domain = data.entities
    magic_entities = data.magic_entities

    # Check feature availability
    if MagicAreasFeatures.LIGHT_GROUPS not in data.enabled_features:
        return

    # Check if there are any lights
    if LIGHT_DOMAIN not in entities_by_domain:
        _LOGGER.debug("%s: No %s entities for area.", area_config.name, LIGHT_DOMAIN)
        return

    light_entities = [e["entity_id"] for e in entities_by_domain[LIGHT_DOMAIN]]
    feature_config = data.feature_configs.get(MagicAreasFeatures.LIGHT_GROUPS, {})

    light_groups = []

    # Create light groups
    if area_config.is_meta():
        light_groups.append(
            MagicLightGroup(
                area_config, coordinator, light_entities, translation_key=LightGroupCategory.ALL
            )
        )
    else:
        child_categories = []

        # Create extended light groups
        for category in LIGHT_GROUP_CATEGORIES:
            category_lights = [
                light_entity
                for light_entity in feature_config.get(category, {})
                if light_entity in light_entities
            ]

            if category_lights:
                _LOGGER.debug(
                    "%s: Creating %s group for area with lights: %s",
                    area_config.name,
                    category,
                    category_lights,
                )
                light_group_object = AreaLightGroup(
                    area_config,
                    coordinator,
                    category_lights,
                    category,
                    feature_config=feature_config,
                )
                light_groups.append(light_group_object)
                child_categories.append(category)

        _LOGGER.debug(
            "%s: Creating Area light group for area with child categories: %s",
            area_config.name,
            str(child_categories),
        )
        light_groups.append(
            AreaLightGroup(
                area_config,
                coordinator,
                light_entities,
                category=LightGroupCategory.ALL,
                child_categories=child_categories,
                feature_config=feature_config,
            )
        )

    # Create all groups
    if light_groups:
        async_add_entities(light_groups)

    if LIGHT_DOMAIN in magic_entities:
        cleanup_removed_entries(hass, light_groups, magic_entities[LIGHT_DOMAIN])


class MagicLightGroup(MagicGroupEntity, LightGroup):
    """Magic Light Group for Meta-areas."""

    feature_info = MagicAreasFeatureInfoLightGroups()

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
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
            name=EMPTY_STRING,
            unique_id=self.unique_id,
            entity_ids=self.member_entity_ids,
            mode=False,
        )
        delattr(self, "_attr_name")

    def _get_active_lights(self) -> list[str]:
        """Return list of lights that are on."""
        active_lights = []
        for entity_id in self._entity_ids:
            light_state = self.hass.states.get(entity_id)
            if not light_state:
                continue
            if light_state.state == STATE_ON:
                active_lights.append(entity_id)

        return active_lights

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Forward the turn_on command to all lights in the light group."""

        data = {
            key: value for key, value in kwargs.items() if key in FORWARDED_ATTRIBUTES
        }

        # Get active lights or default to all lights
        active_lights = self._get_active_lights() or self._entity_ids
        _LOGGER.debug(
            "%s: restricting call to active lights: %s",
            self._area_name,
            str(active_lights),
        )

        data[ATTR_ENTITY_ID] = active_lights

        _LOGGER.debug("%s: Forwarded turn_on command: %s", self._area_name, data)

        await self.hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            data,
            blocking=True,
            context=self._context,
        )


class AreaLightGroup(MagicLightGroup):
    """Magic Light Group."""

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
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

        self.controlling = True
        self.controlled = False

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

        # Build control policy
        self.policy = build_light_group_policy(
            assigned_states=self.assigned_states,
            act_on_modes=self.act_on,
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

    async def _async_setup_group(self) -> None:
        """Set up light group - called by MagicGroupEntity lifecycle."""
        # Resolve child_ids from entity registry (category groups are registered before ALL group)
        if self.category == LightGroupCategory.ALL and self._child_categories:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)
            resolved_ids = []
            for cat in self._child_categories:
                child_uid = f"light_groups_{self._area_id}_{cat}"
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
                self.controlling = controlling
                self._attr_extra_state_attributes["controlling"] = self.controlling
        else:
            self._attr_is_on = False

        # Setup state change listeners
        await self._setup_listeners()

    async def _setup_listeners(self, _: Any = None) -> None:
        """Set up listeners for area state change."""
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

    # State Change Handling

    @callback
    def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle area state change event."""
        if area_id != self._area_id:
            self.logger.debug(
                "%s: Area state change event not for us. Skipping. (req: %s/self: %s)",
                self.name,
                area_id,
                self._area_id,
            )
            return False

        automatic_control = self.is_control_enabled()

        if not automatic_control:
            self.logger.debug(
                "%s: Automatic control for light group is disabled, skipping...",
                self.name,
            )
            return False

        self.logger.debug("%s: Light group detected area state change", self.name)

        # Update cache with fresh states from event snapshot (prevents stale reads)
        _new_states, _lost_states, current_states = states_tuple
        self._last_known_area_states = list(current_states)

        # Handle all lights group
        if self.category == LightGroupCategory.ALL:
            return self.state_change_primary(states_tuple)

        # Handle light category
        return self.state_change_secondary(states_tuple)

    def state_change_primary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle primary state change."""
        # pylint: disable-next=unused-variable
        new_states, lost_states, _current_states = states_tuple

        # If area clear
        if AreaStates.CLEAR in new_states:
            self.logger.debug("%s: Area is clear, should turn off lights!", self.name)
            self.reset_control()
            return self._turn_off()

        return False

    def state_change_secondary(
        self, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> bool:
        """Handle secondary state change."""
        new_states, lost_states, current_states = states_tuple

        # Evaluate policy
        decision = self.policy.evaluate(new_states, lost_states, current_states)
        self.logger.debug("%s: Decision: %s", self.name, decision.reason)

        # Handle control tracking side effects
        if decision.reset_control:
            self.reset_control()
        if decision.should_track_control:
            self.controlled = True

        # Execute action
        if decision.action == LightAction.TURN_ON:
            return self._turn_on()
        elif decision.action == LightAction.TURN_OFF:
            return self._turn_off()
        else:  # NOOP
            return False

    # Light Handling

    def _turn_on(self) -> bool:
        """Turn on light if it's not already on and if we're controlling it."""
        if not self.controlling:
            return False

        if self.is_on:
            return False

        self.controlled = True

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.async_create_task(
            self.hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)
        )

        return True

    def _turn_off(self) -> bool:
        """Turn off light if it's not already off, and we're controlling it."""
        if not self.controlling:
            return False

        if not self.is_on:
            return False

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.async_create_task(
            self.hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)
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
            return False

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self) -> None:
        """Reset control status."""
        self.controlling = True
        self._attr_extra_state_attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()
        self.logger.debug("{self.name}: Control Reset.")

    def is_child_controllable(self, entity_id: str) -> bool:
        """Check if child entity is controllable."""
        entity_object = self.hass.states.get(entity_id)
        if not entity_object:
            return False
        if "controlling" in entity_object.attributes:
            return entity_object.attributes["controlling"]

        return False

    def handle_group_state_change_primary(self) -> None:
        """Handle group state change for primary area state events."""
        controlling = False

        if not self._child_ids:
            return

        for entity_id in self._child_ids:
            if self.is_child_controllable(entity_id):
                controlling = True
                break

        self.controlling = controlling
        self.schedule_update_ha_state()

    def handle_group_state_change_secondary(self) -> None:
        """Handle group state change for secondary area state events."""
        # If we changed last, unset
        if self.controlled:
            self.controlled = False
            self.logger.debug("%s: Group controlled by us.", self.name)
        else:
            # If not, it was manually controlled, stop controlling
            self.controlling = False
            self.logger.debug("%s: Group controlled by something else.", self.name)

    @callback
    def group_state_changed(self, event: Event[EventStateChangedData]) -> bool:
        """Handle group state change events."""
        # If area is not occupied, ignore
        # Read fresh state from HA (not cached), to avoid stale reads
        entity_registry = entity_registry_module.async_get(self.hass)
        presence_entity_id = entity_registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"presence_tracking_{self._area_id}_area_state",
        )
        current_area_states = []
        if presence_entity_id:
            state = self.hass.states.get(presence_entity_id)
            if state and "states" in state.attributes:
                current_area_states = [
                    str(s.value) if isinstance(s, Enum) else str(s)
                    for s in state.attributes["states"]
                ]
        if AreaStates.OCCUPIED.value not in current_area_states:
            self.reset_control()
        else:
            if not event.context:
                return False
            origin_event = event.context.origin_event

            if self.category == LightGroupCategory.ALL:
                self.handle_group_state_change_primary()
            else:
                # Ignore certain events
                if origin_event and origin_event.event_type == "state_changed":
                    # Skip non-ON/OFF state changes
                    if (
                        "old_state" not in origin_event.data
                        or not origin_event.data["old_state"]
                        or not origin_event.data["old_state"].state
                        or origin_event.data["old_state"].state
                        not in [
                            STATE_ON,
                            STATE_OFF,
                        ]
                    ):
                        return False
                    if (
                        "new_state" not in origin_event.data
                        or not origin_event.data["new_state"]
                        or not origin_event.data["new_state"].state
                        or origin_event.data["new_state"].state
                        not in [
                            STATE_ON,
                            STATE_OFF,
                        ]
                    ):
                        return False

                    # Skip restored events
                    if (
                        "restored" in origin_event.data["old_state"].attributes
                        and origin_event.data["old_state"].attributes["restored"]
                    ):
                        return False

                self.handle_group_state_change_secondary()

        # Update attribute
        self._attr_extra_state_attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()

        return True
