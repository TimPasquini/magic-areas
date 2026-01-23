"""Classes for Magic Areas and Meta Areas."""

import asyncio
import logging
import random
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_ON,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import (
    EventDeviceRegistryUpdatedData,
)
from homeassistant.helpers.device_registry import (
    async_get as devicereg_async_get,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity_registry import (
    EventEntityRegistryUpdatedData,
    RegistryEntry,
)
from homeassistant.helpers.entity_registry import (
    async_get as entityreg_async_get,
)
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from custom_components.magic_areas.area_constants import (
    AREA_STATE_OCCUPIED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_TYPE,
    DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES,
)
from custom_components.magic_areas.enums import (
    MagicAreasEvents,
    MetaAreaAutoReloadSettings,
    MetaAreaType,
)
from custom_components.magic_areas.core.config import (
    has_configured_state,
    normalize_feature_config,
)
from custom_components.magic_areas.core.area_model import AreaDescriptor
from custom_components.magic_areas.core.entities import (
    EntitySnapshot,
    build_entity_dict,
    group_entities,
)
from custom_components.magic_areas.core.meta import (
    build_meta_presence_sensors,
    resolve_active_areas,
    resolve_child_areas,
)
from custom_components.magic_areas.core.presence import build_presence_sensors
from custom_components.magic_areas.models import MagicAreasConfigEntry

if TYPE_CHECKING:
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
        self._area_entities: list[str] = []
        self._area_devices: list[str] = []

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
        self.logger.debug(
            "%s (%s) initialized.", self.name, "Meta-Area" if self.is_meta() else "Area"
        )

        @callback
        async def _async_notify_load(*args: Any, **kwargs: Any) -> None:
            """Notify that area is loaded."""
            # Announce area type loaded
            dispatcher_send(
                self.hass,
                MagicAreasEvents.AREA_LOADED,
                self.area_type,
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
        return self.has_state(AREA_STATE_OCCUPIED)

    def get_current_states(self) -> list[str]:
        """Return the most recent area states from the area sensor if available."""
        if self.states:
            return list(self.states)
        area_sensor_entity_id = (
            f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{self.slug}_area_state"
        )
        area_sensor_state = self.hass.states.get(area_sensor_entity_id)
        if (
            area_sensor_state
            and "states" in area_sensor_state.attributes
            and area_sensor_state.attributes["states"]
        ):
            normalized: list[str] = []
            for state in area_sensor_state.attributes["states"]:
                if isinstance(state, Enum):
                    normalized.append(str(state.value))
                else:
                    normalized.append(str(state))
            return normalized
        return list(self.states)

    def has_state(self, state: str) -> bool:
        """Check if area has a given state."""
        value = state.value if isinstance(state, Enum) else state
        return str(value) in [str(item) for item in self.get_current_states()]

    def has_configured_state(self, state: str) -> bool:
        """Check if area supports a given state."""
        return has_configured_state(self.config, state)

    def has_feature(self, feature: str) -> bool:
        """Check if area has a given feature."""
        enabled_features = self.config.get(CONF_ENABLED_FEATURES)
        if enabled_features is not None and not isinstance(enabled_features, (list, dict)):
            self.logger.warning(
                "%s: Invalid configuration for %s", self.name, CONF_ENABLED_FEATURES
            )
        enabled, _ = normalize_feature_config(self.config)
        return feature in enabled

    def feature_config(self, feature: str) -> dict:
        """Return configuration for a given feature."""
        enabled, feature_configs = normalize_feature_config(self.config)
        if feature not in enabled:
            self.logger.debug("%s: Feature '%s' not enabled.", self.name, feature)
            return {}

        if not feature_configs:
            self.logger.debug("%s: No feature config found for %s", self.name, feature)

        return feature_configs.get(feature, {})

    def available_platforms(self) -> list[str]:
        """Return available platforms to area type."""

        if not self.is_meta():
            available_platforms = MAGIC_AREAS_COMPONENTS
        else:
            available_platforms = (
                MAGIC_AREAS_COMPONENTS_GLOBAL
                if self.id == META_AREA_GLOBAL.lower()
                else MAGIC_AREAS_COMPONENTS_META
            )

        return available_platforms

    @property
    def area_type(self) -> str | None:
        """Return the area type."""
        return self.config.get(CONF_TYPE)

    def is_meta(self) -> bool:
        """Return if area is Meta or not."""
        return self.area_type == AREA_TYPE_META

    def is_interior(self) -> bool:
        """Return if area type is interior or not."""
        return self.area_type == AREA_TYPE_INTERIOR

    def is_exterior(self) -> bool:
        """Return if area type is exterior or not."""
        return self.area_type == AREA_TYPE_EXTERIOR

    def _is_magic_area_entity(self, entity: RegistryEntry) -> bool:
        """Return if entity belongs to this integration instance."""
        return entity.config_entry_id == self.hass_config.entry_id

    def _should_exclude_entity(self, entity: RegistryEntry) -> bool:
        """Exclude entity."""

        # Is magic_area entity?
        if entity.config_entry_id == self.hass_config.entry_id:
            return True

        # Is disabled?
        if entity.disabled:
            return True

        # Is in the exclusion list?
        if entity.entity_id in self.config.get(CONF_EXCLUDE_ENTITIES, []):
            return True

        # Are we excluding DIAGNOSTIC and CONFIG?
        if self.config.get(
            CONF_IGNORE_DIAGNOSTIC_ENTITIES, DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES
        ):
            if entity.entity_category in [
                EntityCategory.CONFIG,
                EntityCategory.DIAGNOSTIC,
            ]:
                return True

        return False

    async def load_entities(self) -> None:
        """Load entities into entity list."""

        entity_list: list[RegistryEntry] = []
        include_entities = self.config.get(CONF_INCLUDE_ENTITIES)

        entity_registry = entityreg_async_get(self.hass)
        device_registry = devicereg_async_get(self.hass)

        # Add entities from devices in this area
        devices_in_area = device_registry.devices.get_devices_for_area_id(self.id)
        for device in devices_in_area:
            entity_list.extend(
                [
                    entity
                    for entity in entity_registry.entities.get_entries_for_device_id(
                        device.id
                    )
                    if not self._should_exclude_entity(entity)
                ]
            )
            self._area_devices.append(device.id)

        # Add entities that are specifically set as this area but device is not or has no device.
        entities_in_area = entity_registry.entities.get_entries_for_area_id(self.id)
        entity_list.extend(
            [
                entity
                for entity in entities_in_area
                if entity.entity_id not in entity_list
                and not self._should_exclude_entity(entity)
            ]
        )

        if include_entities and isinstance(include_entities, list):
            for include_entity in include_entities:
                entity_entry = entity_registry.async_get(include_entity)
                if entity_entry:
                    entity_list.append(entity_entry)

        self.load_entity_list(entity_list)

        self.logger.debug(
            "%s: Found area entities: %s",
            self.name,
            str(self.entities),
        )

    def load_magic_entities(self) -> None:
        """Load magic areas-generated entities."""

        entity_registry = entityreg_async_get(self.hass)

        # Add magic are entities
        entities_for_config_id = (
            entity_registry.entities.get_entries_for_config_entry_id(
                self.hass_config.entry_id
            )
        )

        for entity_id in [entity.entity_id for entity in entities_for_config_id]:
            entity_domain = entity_id.split(".")[0]

            if entity_domain not in self.magic_entities:
                self.magic_entities[entity_domain] = []

            self.magic_entities[entity_domain].append(self.get_entity_dict(entity_id))

        self.logger.debug(
            "%s: Loaded magic entities: %s", self.name, str(self.magic_entities)
        )

    def get_entity_dict(self, entity_id: str) -> dict[str, str]:
        """Return entity_id in a dictionary with attributes (if available)."""

        # Get latest state and create object
        latest_state = self.hass.states.get(entity_id)
        attributes = latest_state.attributes if latest_state else None
        return build_entity_dict(entity_id, attributes)

    def load_entity_list(self, entity_list: list[RegistryEntry]) -> None:
        """Populate entity list with loaded entities."""
        self.logger.debug("%s: Original entity list: %s", self.name, str(entity_list))
        snapshots: list[EntitySnapshot] = []

        for entity in entity_list:
            if entity.entity_id in self._area_entities:
                continue
            self.logger.debug("%s: Loading entity: %s", self.name, entity.entity_id)

            try:
                if not entity.domain:
                    self.logger.warning(
                        "%s: Entity domain not found for %s", self.name, entity
                    )
                    continue
                latest_state = self.hass.states.get(entity.entity_id)
                snapshots.append(
                    EntitySnapshot(
                        entity_id=entity.entity_id,
                        domain=entity.domain,
                        attributes=latest_state.attributes if latest_state else None,
                    )
                )

                self._area_entities.append(entity.entity_id)

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as err:
                self.logger.error(
                    "%s: Unable to load entity '%s': %s",
                    self.name,
                    entity,
                    str(err),
                )

        grouped = group_entities(snapshots)
        for domain, entities in grouped.items():
            self.entities.setdefault(domain, []).extend(entities)

        # Load our own entities
        self.load_magic_entities()

    def get_presence_sensors(self) -> list[str]:
        """Return list of entities used for presence tracking."""
        enabled, _ = normalize_feature_config(self.config)
        return build_presence_sensors(
            entities_by_domain=self.entities,
            config=self.config,
            slug=self.slug,
            enabled_features=enabled,
        )

    async def initialize(self, _: Any = None) -> None:
        """Initialize area."""
        self.logger.debug("%s: Initializing area...", self.name)

        await self.load_entities()

        self.finalize_init()

    def has_entities(self, domain: str) -> bool:
        """Check if area has entities."""
        return domain in self.entities

    def make_entity_registry_filter(
        self,
    ) -> Callable[[EventEntityRegistryUpdatedData], bool]:
        """Create entity register filter for this area."""

        @callback
        def _entity_registry_filter(event_data: EventEntityRegistryUpdatedData) -> bool:
            """Filter entity registry events relevant to this area."""

            entity_id = event_data["entity_id"]

            # Ignore our own stuff
            _, entity_part = entity_id.split(".")
            if entity_part.startswith(MAGICAREAS_UNIQUEID_PREFIX):
                return False

            # Ignore if too soon
            if dt_util.utcnow() - self.timestamp < timedelta(
                seconds=MetaAreaAutoReloadSettings.THROTTLE
            ):
                return False

            entity_registry = entityreg_async_get(self.hass)
            entity_entry = entity_registry.async_get(entity_id)

            if event_data["action"] == "update" and "area_id" in event_data["changes"]:
                # Removed from our area
                if event_data["changes"].get("area_id") == self.id:
                    return True

                # Is from our area
                if entity_entry and entity_entry.area_id == self.id:
                    return True

                return False

            if event_data["action"] in ("create", "remove"):
                # Is from our area
                if entity_entry and entity_entry.area_id == self.id:
                    return True

            return False

        return _entity_registry_filter

    def make_device_registry_filter(
        self,
    ) -> Callable[[EventDeviceRegistryUpdatedData], bool]:
        """Create device register filter for this area."""

        @callback
        def _device_registry_filter(event_data: EventDeviceRegistryUpdatedData) -> bool:
            """Filter device registry events relevant to this area."""

            # Ignore our own stuff
            if event_data["device_id"].startswith(MAGIC_DEVICE_ID_PREFIX):
                return False

            # Ignore if too soon
            if dt_util.utcnow() - self.timestamp < timedelta(
                seconds=MetaAreaAutoReloadSettings.THROTTLE
            ):
                return False

            if event_data["action"] == "update" and "area_id" in event_data["changes"]:
                # Removed from our area
                if event_data["changes"].get("area_id") == self.id:
                    return True

            # Was from our area?
            if event_data["device_id"] in self._area_devices:
                return True

            device_registry = devicereg_async_get(self.hass)
            device_entry = device_registry.async_get(event_data["device_id"])

            # Is from our area
            if device_entry and device_entry.area_id == self.id:
                return True

            return False

        return _device_registry_filter


class MagicMetaArea(MagicArea):
    """Magic Meta Area class."""

    def __init__(
        self,
        hass: HomeAssistant,
        area: BasicArea,
        config: "MagicAreasConfigEntry",
    ) -> None:
        """Initialize the meta magic area with all the stuff."""
        super().__init__(hass, area, config)
        self.child_areas: list[str] = self.get_child_areas()

    def _collect_area_descriptors(self) -> list[AreaDescriptor]:
        """Return descriptors for all loaded areas."""
        entries = self.hass.config_entries.async_entries("magic_areas")
        descriptors: list[AreaDescriptor] = []

        for entry in entries:
            if entry.state != ConfigEntryState.LOADED:
                continue

            if entry.domain != "magic_areas":
                continue

            area: MagicArea = entry.runtime_data.area
            area_type = area.config.get(CONF_TYPE, area.id)
            descriptors.append(
                AreaDescriptor(
                    id=area.id,
                    slug=area.slug,
                    floor_id=area.floor_id,
                    area_type=str(area_type),
                    is_meta=area.is_meta(),
                )
            )

        return descriptors

    def get_presence_sensors(self) -> list[str]:
        """Return list of entities used for presence tracking."""
        return build_meta_presence_sensors(self.child_areas)

    def get_active_areas(self) -> list[str]:
        """Return areas that are occupied."""
        state_map: dict[str, str] = {}

        for area in self.child_areas:
            try:
                entity_id = (
                    f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{area}_area_state"
                )
                entity = self.hass.states.get(entity_id)

                if not entity:
                    self.logger.debug("%s: Unable to get area state entity.", area)
                    continue

                state_map[area] = entity.state

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                self.logger.error(
                    "%s: Unable to get active area state: %s", area, str(e)
                )

        return resolve_active_areas(self.child_areas, state_map)

    def get_child_areas(self) -> list[str]:
        """Return areas that a Meta area is watching."""
        meta_descriptor = AreaDescriptor(
            id=self.id,
            slug=self.slug,
            floor_id=self.floor_id,
            area_type=str(self.id),
            is_meta=True,
        )
        return resolve_child_areas(meta_descriptor, self._collect_area_descriptors())

    async def initialize(self, _: Any = None) -> None:
        """Initialize Meta area."""
        if self.initialized:
            self.logger.debug("%s: Already initialized, ignoring.", self.name)
            return None

        self.logger.debug("%s: Initializing meta area...", self.name)

        await self.load_entities()

        self.finalize_init()
        return None

    async def load_entities(self) -> None:
        """Load entities into entity list."""

        entity_registry = entityreg_async_get(self.hass)
        entity_list: list[RegistryEntry] = []

        entries = self.hass.config_entries.async_entries("magic_areas")
        for entry in entries:
            if entry.state != ConfigEntryState.LOADED:
                continue

            # We need to cast here because we know it's a MagicAreasConfigEntry
            # but the type system doesn't know that yet
            if entry.domain != "magic_areas":
                continue
            entry = entry

            area: MagicArea = entry.runtime_data.area

            if area.slug not in self.child_areas:
                continue

            # Force loading of magic entities
            area.load_magic_entities()

            for entities in area.magic_entities.values():
                for entity in entities:
                    if not isinstance(entity[ATTR_ENTITY_ID], str):
                        self.logger.debug(
                            "%s: Entity ID is not a string: '%s' (probably a group, skipping)",
                            self.name,
                            str(entity[ATTR_ENTITY_ID]),
                        )
                        continue

                    # Skip excluded entities
                    if entity[ATTR_ENTITY_ID] in self.config.get(
                        CONF_EXCLUDE_ENTITIES, []
                    ):
                        continue

                    entity_entry = entity_registry.async_get(entity[ATTR_ENTITY_ID])
                    if not entity_entry:
                        self.logger.debug(
                            "%s: Magic Entity not found on Entity Registry: %s",
                            self.name,
                            entity[ATTR_ENTITY_ID],
                        )
                        continue
                    entity_list.append(entity_entry)

        self.load_entity_list(entity_list)

        self.logger.debug(
            "%s: Loaded entities for meta area: %s", self.name, str(self.entities)
        )

    def finalize_init(self) -> None:
        """Finalize Meta-Area initialization."""

        async_dispatcher_connect(
            self.hass, MagicAreasEvents.AREA_LOADED, self._handle_loaded_area
        )

    @callback
    async def _handle_loaded_area(
        self, area_type: str, floor_id: int | None, area_id: str
    ) -> None:
        """Handle area loaded signals."""

        self.logger.debug(
            "%s: Received area loaded signal (type=%s, floor_id=%s, area_id=%s)",
            self.name,
            area_type,
            floor_id,
            area_id,
        )

        # Don't act while hass is not running
        if not self.hass.is_running:
            return None

        # Ignore if already handling it
        if self.reloading:
            return None

        # Handle Global
        if self.slug == MetaAreaType.GLOBAL:
            return await self.reload()

        # Handle all non-Global meta-areas including floors
        self.logger.info(
            "SS %s, AT %s, AI %s, CA: %s",
            self.slug,
            area_type,
            area_id,
            str(self.child_areas),
        )
        if area_type == self.slug or area_id in self.child_areas:
            return await self.reload()
        return None

    async def reload(self) -> None:
        """Reload current entry."""
        if dt_util.utcnow() - self._last_reload < timedelta(
            seconds=MetaAreaAutoReloadSettings.THROTTLE
        ):
            return

        self.logger.info("%s: Reloading entry.", self.name)
        self._last_reload = dt_util.utcnow()

        # Give some time for areas to finish loading,
        # randomize to prevent staggering the CPU with
        # stacked reloads.
        max_delay: float = (
            MetaAreaAutoReloadSettings.DELAY_MULTIPLIER
            * MetaAreaAutoReloadSettings.DELAY
        )
        delay: float = random.uniform(
            MetaAreaAutoReloadSettings.DELAY,
            max_delay,
        )

        # Make Global load last
        if self.slug == MetaAreaType.GLOBAL:
            delay = max_delay

        self.reloading = True
        await asyncio.sleep(delay)

        self.hass.config_entries.async_schedule_reload(self.hass_config.entry_id)
