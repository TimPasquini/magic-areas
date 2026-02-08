"""The basic entities for magic areas."""

from collections.abc import Callable
import logging

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.area_constants import (
    META_AREAS,
)
from custom_components.magic_areas.components import (
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
)
from custom_components.magic_areas.feature_info import MagicAreasFeatureInfo

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea
    feature_info: MagicAreasFeatureInfo | None = None
    _extra_identifiers: list[str] | None = None
    _attr_has_entity_name = True

    def __init__(
        self,
        area: MagicArea,
        domain: str,
        translation_key: str | None = None,
        extra_identifiers: list[str] | None = None,
    ) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        if not self.feature_info:
            raise NotImplementedError(f"{self.name}: Feature info not set.")

        self.logger = logging.getLogger(type(self).__module__)
        self.area = area
        self._extra_identifiers = []

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
            self.area.name,
            self.entity_id,
            self._attr_unique_id,
            self._attr_translation_key,
        )

    def _generate_entity_id(self, domain: str) -> str:
        if not self.feature_info:
            raise NotImplementedError(f"{self.name}: Feature info not set.")

        entity_id_parts = [
            MAGICAREAS_UNIQUEID_PREFIX,
            self.feature_info.id,
            self.area.slug,
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
        if not self.feature_info:
            raise NotImplementedError(f"{self.name}: Feature info not set.")

        unique_id_parts = [
            self.feature_info.id,
            self.area.id,
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
        return getattr(self.area, "last_update_success", True)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.area.id}")
            },
            name=self.area.name,
            manufacturer="Magic Areas",
            model="Magic Area",
            translation_key=(
                self.area.slug
                if (self.area.is_meta() and self.area.name in META_AREAS)
                else None
            ),
        )

    def get_feature_config(self) -> dict:
        """Get feature config from coordinator snapshot with fallback.

        Reads from coordinator snapshot when available (preferred),
        falls back to area.feature_config() during initialization.

        Returns:
            Feature configuration dict (empty if feature not enabled)
        """
        if not self.feature_info:
            return {}

        # Try coordinator snapshot first (single source of truth)
        runtime_data = getattr(self.area.hass_config, "runtime_data", None)
        if runtime_data and runtime_data.coordinator.data:
            return runtime_data.coordinator.data.feature_configs.get(
                self.feature_info.id, {}
            )

        # Fallback to area method (during init before coordinator ready)
        return self.area.feature_config(self.feature_info.id)

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
    _group_listeners: list[tuple[str, Callable[[], None]]]

    def __init__(
        self,
        area: MagicArea,
        domain: str,
        member_entity_ids: list[str],
        translation_key: str | None = None,
        extra_identifiers: list[str] | None = None,
    ) -> None:
        """Initialize group entity.

        Args:
            area: Magic area instance
            domain: Home Assistant domain (light, sensor, etc.)
            member_entity_ids: List of entity IDs in this group
            translation_key: Optional translation key
            extra_identifiers: Optional extra unique ID identifiers
        """
        super().__init__(area, domain, translation_key, extra_identifiers)
        self._member_entity_ids = member_entity_ids
        self._group_listeners = []

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
        """Hook for subclass-specific group setup.

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
        for listener_name, remove_callback in self._group_listeners:
            _LOGGER.debug(
                "%s: Removing listener: %s",
                self.name,
                listener_name,
            )
            try:
                remove_callback()
            except Exception as err:
                _LOGGER.warning(
                    "%s: Error removing listener %s: %s",
                    self.name,
                    listener_name,
                    err,
                )

        self._group_listeners.clear()

        # Call hook for subclass-specific cleanup
        await self._async_teardown_group()

        await super().async_will_remove_from_hass()

    async def _async_teardown_group(self) -> None:
        """Hook for subclass-specific group cleanup.

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
        self._group_listeners.append((name, remove_callback))
        _LOGGER.debug(
            "%s: Tracking listener: %s (total: %d)",
            self.name,
            name,
            len(self._group_listeners),
        )

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
