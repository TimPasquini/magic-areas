"""The basic entities for magic areas."""

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.area_state import META_AREAS
from custom_components.magic_areas.components import (
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
)
from custom_components.magic_areas.core.feature_access import (
    get_feature_config,
)
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import FeatureInfo, get_feature_info

if TYPE_CHECKING:
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    feature_id: MagicAreasFeatures | None = None
    _extra_identifiers: list[str] | None = None
    _attr_has_entity_name = True
    _area_config: "AreaConfig"
    _coordinator: "MagicAreasCoordinator"
    _feature_info: FeatureInfo

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        domain: str,
        translation_key: str | None = None,
        extra_identifiers: list[str] | None = None,
    ) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        if not self.feature_id:
            raise NotImplementedError(f"{self.name}: Feature id not set.")

        self.logger = logging.getLogger(type(self).__module__)
        self._area_config = area_config
        self._coordinator = coordinator
        self._extra_identifiers = []
        self._feature_info = get_feature_info(self.feature_id)

        # Cache area identity fields (reduces coupling to MagicArea)
        self._area_id = area_config.id
        self._area_name = area_config.name
        self._area_slug = area_config.slug
        self._area_icon = area_config.icon
        self._is_meta = area_config.is_meta()

        if extra_identifiers:
            self._extra_identifiers.extend(extra_identifiers)

        # Allow supplying of additional translation key parts
        # for dealing with device_classes
        translation_key_parts = []
        feature_translation_key = self.feature_info.translation_keys[domain]
        if feature_translation_key:
            translation_key_parts.append(feature_translation_key)
        if translation_key:
            translation_key_parts.append(translation_key)
        self._attr_translation_key = "_".join(translation_key_parts)
        self._attr_translation_placeholders = {}

        # Resolve icon
        self._attr_icon = self.feature_info.icons.get(domain, None)

        # Resolve entity id & unique id
        self.entity_id = self._generate_entity_id(domain)
        self._attr_unique_id = self._generate_unique_id(domain)

        _LOGGER.debug(
            "%s: Initializing entity. (entity_id: %s, unique id: %s, translation_key: %s)",
            self._area_name,
            self.entity_id,
            self._attr_unique_id,
            self._attr_translation_key,
        )

    def _generate_entity_id(self, domain: str) -> str:
        if not self.feature_id:
            raise NotImplementedError(f"{self.name}: Feature id not set.")

        entity_id_parts = [
            MAGICAREAS_UNIQUEID_PREFIX,
            self.feature_info.id,
            self._area_slug,
        ]

        if (
            self._attr_translation_key
            and self._attr_translation_key != self.feature_info.id
        ):
            entity_id_parts.append(self._attr_translation_key)

        if self._extra_identifiers:
            entity_id_parts.extend(self._extra_identifiers)

        entity_id = "_".join(entity_id_parts)

        return f"{domain}.{entity_id}"

    def _generate_unique_id(self, domain: str, extra_parts: list | None = None) -> str:
        # Format: feature_area_id_[translation]_[extra...]
        if not self.feature_id:
            raise NotImplementedError(f"{self.name}: Feature id not set.")

        unique_id_parts = [
            self.feature_info.id,
            self._area_id,
        ]

        if (
            self._attr_translation_key
            and self._attr_translation_key != self.feature_info.id
        ):
            unique_id_parts.append(self._attr_translation_key)

        if self._extra_identifiers:
            unique_id_parts.extend(self._extra_identifiers)

        return "_".join(unique_id_parts)

    @property
    def should_poll(self) -> bool:
        """If entity should be polled."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Read from coordinator's last_update_success (managed by DataUpdateCoordinator)
        return self._coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self._area_id}")
            },
            name=self._area_name,
            manufacturer="Magic Areas",
            model="Magic Area",
            translation_key=(
                self._area_slug
                if (self._is_meta and self._area_name in META_AREAS)
                else None
            ),
        )

    def get_feature_config(self) -> dict:
        """Get feature config from coordinator snapshot.

        Returns:
            Feature configuration dict (empty if feature not enabled)

        """
        return get_feature_config(self._coordinator, self.feature_id)

    @property
    def feature_info(self) -> FeatureInfo:
        """Return feature metadata for the entity."""
        return self._feature_info

    async def restore_state(self) -> None:
        """Restore the state of the entity."""
        last_state = await self.async_get_last_state()

        if last_state is None:
            _LOGGER.debug("%s: New entity created", self.name)
            self._attr_state = STATE_OFF
        else:
            _LOGGER.debug(
                "%s: entity restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._attr_state = last_state.state
            self._attr_extra_state_attributes = dict(last_state.attributes)

        self.schedule_update_ha_state()


class MagicGroupEntity(MagicEntity):
    """Base class for all Magic Areas group entities.

    Provides standardized lifecycle management for group entities:
    - Consistent setup/teardown pattern
    - Member entity tracking
    - Listener cleanup on removal
    - Single place for group-wide behavior changes

    This eliminates the inconsistencies that cause flaky group tests.
    """

    _member_entity_ids: list[str]
    _listener_registry: ListenerRegistry

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        domain: str,
        member_entity_ids: list[str],
        translation_key: str | None = None,
        extra_identifiers: list[str] | None = None,
    ) -> None:
        """Initialize group entity.

        Args:
            area_config: Area configuration
            coordinator: Magic areas coordinator
            domain: Home Assistant domain (light, sensor, etc.)
            member_entity_ids: List of entity IDs in this group
            translation_key: Optional translation key
            extra_identifiers: Optional extra unique ID identifiers

        """
        super().__init__(area_config, coordinator, domain, translation_key, extra_identifiers)
        self._member_entity_ids = member_entity_ids
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    async def async_added_to_hass(self) -> None:
        """Set up group entity with standard lifecycle.

        This ensures all group entities follow the same setup pattern:
        1. Parent setup (MagicEntity)
        2. Group-specific setup (subclass hook)
        3. Initial state write

        Override _async_setup_group() for group-specific setup, not this method.
        """
        await super().async_added_to_hass()

        # Call hook for subclass-specific setup
        await self._async_setup_group()

        # Write initial state (always last to ensure state is calculated)
        self.async_write_ha_state()

    async def _async_setup_group(self) -> None:
        """Set up subclass-specific group configuration.

        Override this in subclasses that need custom setup logic.
        Called during async_added_to_hass before initial state write.
        """
        pass

    async def async_will_remove_from_hass(self) -> None:
        """Tear down group entity with standard lifecycle.

        This ensures all group entities follow the same teardown pattern:
        1. Clean up tracked listeners
        2. Group-specific cleanup (subclass hook)
        3. Parent cleanup (MagicEntity)

        Override _async_teardown_group() for group-specific cleanup, not this method.
        """
        # Clean up all tracked listeners
        self._listener_registry.cleanup()

        # Call hook for subclass-specific cleanup
        await self._async_teardown_group()

        await super().async_will_remove_from_hass()

    async def _async_teardown_group(self) -> None:
        """Tear down subclass-specific group configuration.

        Override this in subclasses that need custom cleanup logic.
        Called during async_will_remove_from_hass after listener cleanup.
        """
        pass

    def track_group_listener(
        self, remove_callback: Callable[[], None], name: str = "unnamed"
    ) -> None:
        """Track a listener for automatic cleanup on entity removal.

        Use this to register any state listeners, event subscriptions, etc.
        that need cleanup when the group entity is removed.

        Args:
            remove_callback: Function to call to remove the listener
            name: Descriptive name for debugging (e.g., "state_change_listener")

        Example:
            remove = async_track_state_change_event(...)
            self.track_group_listener(remove, "member_state_tracking")

        """
        self._listener_registry.track(name, remove_callback)

    @property
    def member_entity_ids(self) -> list[str]:
        """Return member entity IDs for this group."""
        return self._member_entity_ids


class BinaryMagicEntity(MagicEntity):
    """Class for Binary-based magic entities."""

    _attr_is_on: bool

    async def restore_state(self) -> None:
        """Restore the state of the entity."""
        last_state = await self.async_get_last_state()

        if last_state is None:
            _LOGGER.debug("%s: New entity created", self.name)
            self._attr_is_on = False
        else:
            _LOGGER.debug(
                "%s: entity restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)

        self.schedule_update_ha_state()
