"""Classes for Magic Areas and Meta Areas."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_registry import (
    async_get as entityreg_async_get,
)
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from custom_components.magic_areas.area_state import (
    AreaStates,
    AreaType,
)
from custom_components.magic_areas.attrs import ATTR_STATES
from custom_components.magic_areas.config_keys import CONF_TYPE
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.models import MagicAreasConfigEntry

# Classes


class BasicArea:
    """An interchangeable area object for Magic Areas to consume."""

    id: str
    name: str
    icon: str | None = None
    floor_id: str | None = None
    is_meta: bool = False


class MagicArea:
    """Magic Area class.

    Tracks entities and updates area states and secondary states.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        area: BasicArea,
        config: "MagicAreasConfigEntry",
    ) -> None:
        """Initialize the magic area with all the stuff."""
        self.hass: HomeAssistant = hass
        self.name: str = area.name
        # Default to the icon for the area.
        self.icon: str | None = area.icon
        self.id: str = area.id
        self.slug: str = slugify(self.name)
        self.hass_config: MagicAreasConfigEntry = config
        self.initialized: bool = False
        self.floor_id: str | None = area.floor_id
        self.logger = logging.getLogger(__name__)

        # Faster lookup lists

        # Track coordinator availability status
        self.last_update_success: bool = True

        # Timestamp for initialization / reload tests
        self.timestamp: datetime = dt_util.utcnow()
        self.reloading: bool = False
        self._last_reload: datetime = datetime.min.replace(tzinfo=dt_util.UTC)

        # Merged options
        area_config = dict(config.data)
        if config.options:
            area_config.update(config.options)
        self.config: dict[str, Any] = area_config

        self.entities: dict[str, list[dict[str, str]]] = {}
        self.magic_entities: dict[str, list[dict[str, str]]] = {}

        self.last_changed: datetime = dt_util.utcnow()

        self.states: list[str] = []

        self.loaded_platforms: list[str] = []

        self.logger.debug("%s: Primed for initialization.", self.name)

    def finalize_init(self) -> None:
        """Finalize initialization of the area."""
        self.initialized = True
        is_meta = self.config.get(CONF_TYPE) == AreaType.META
        self.logger.debug(
            "%s (%s) initialized.", self.name, "Meta-Area" if is_meta else "Area"
        )

        @callback
        async def _async_notify_load(*args: Any, **kwargs: Any) -> None:
            """Notify that area is loaded."""
            # Announce area type loaded
            dispatcher_send(
                self.hass,
                MagicAreasEvents.AREA_LOADED,
                self.config.get(CONF_TYPE),
                self.floor_id,
                self.id,
            )

        # Wait for Hass to have started before announcing load events.
        if self.hass.is_running:
            self.hass.create_task(_async_notify_load())
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _async_notify_load
            )

    def is_occupied(self) -> bool:
        """Return if area is occupied."""
        return self.has_state(AreaStates.OCCUPIED)

    def get_current_states(self) -> list[str]:
        """Return current area states from the HA state machine.

        Reads ATTR_STATES from the published area state binary sensor entity.
        This is the single source of truth — never reads from the mutable
        self.states field.
        """
        entity_registry = entityreg_async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id(
            BINARY_SENSOR_DOMAIN,
            DOMAIN,
            f"presence_tracking_{self.id}_area_state",
        )
        if entity_id:
            state = self.hass.states.get(entity_id)
            if state and ATTR_STATES in state.attributes:
                return [
                    str(s.value) if isinstance(s, Enum) else str(s)
                    for s in state.attributes[ATTR_STATES]
                ]
        return []

    def has_state(self, state: str) -> bool:
        """Check if area has a given state."""
        value = state.value if isinstance(state, Enum) else state
        return str(value) in [str(item) for item in self.get_current_states()]

    async def initialize(self, _: Any = None) -> None:
        """Initialize area."""
        self.logger.debug("%s: Initializing area...", self.name)

        self.finalize_init()
