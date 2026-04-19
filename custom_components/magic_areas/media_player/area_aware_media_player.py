"""Area aware media player, media player component."""

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, TypedDict

from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerState,
    SERVICE_PLAY_MEDIA,
    MediaPlayerEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.entity import MagicEntity
from custom_components.magic_areas.const import DOMAIN as MA_DOMAIN
from custom_components.magic_areas.core.runtime_model import build_presence_tracking_unique_id
from custom_components.magic_areas.core.controls.policies.media import (
    evaluate_area_routing,
)
from custom_components.magic_areas.defaults import DEFAULT_NOTIFY_STATES
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class AreaMediaData(TypedDict):
    """Runtime data required to route media for one area."""

    entities_by_domain: Mapping[str, list[Mapping[str, str]]]
    notification_devices: list[str]
    notification_states: list[str]


class AreaAwareMediaPlayer(MagicEntity, MediaPlayerEntity):
    """Area-aware media player."""

    feature_id = MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        areas_data: dict[str, AreaMediaData],
    ) -> None:
        """Initialize area-aware media player."""
        MagicEntity.__init__(
            self, area_config, coordinator, domain=MEDIA_PLAYER_DOMAIN
        )
        MediaPlayerEntity.__init__(self)

        self._attr_extra_state_attributes: dict[str, object] = {}
        self._state: MediaPlayerState | None = MediaPlayerState.IDLE

        self.areas_data = areas_data
        self._tracked_entities: list[str] = []

        for _area_id, area_data in self.areas_data.items():
            entity_list = self.get_media_players_for_area(
                area_data["entities_by_domain"],
                area_data["notification_devices"],
            )
            if entity_list:
                self._tracked_entities.extend(entity_list)

        _LOGGER.debug("AreaAwareMediaPlayer loaded.")

    def _resolve_area_state_sensor(self, area_id: str) -> str | None:
        """Resolve area state sensor from entity registry."""
        return er.async_get(self.hass).async_get_entity_id(
            BS_DOMAIN,
            MA_DOMAIN,
            build_presence_tracking_unique_id(area_id=area_id),
        )

    def update_attributes(self) -> None:
        """Update entity attributes."""
        area_sensors = []
        for area_id in self.areas_data:
            area_sensor = self._resolve_area_state_sensor(area_id)
            if area_sensor:
                area_sensors.append(area_sensor)
        self._attr_extra_state_attributes["areas"] = area_sensors
        self._attr_extra_state_attributes["entity_id"] = self._tracked_entities

    @staticmethod
    def get_media_players_for_area(
        entities_by_domain: Mapping[str, list[Mapping[str, str]]],
        notification_devices: list[str],
    ) -> set[str]:
        """Return media players for a given area."""
        entity_ids = []

        if MEDIA_PLAYER_DOMAIN not in entities_by_domain:
            return set()
        area_media_players = [
            entity["entity_id"] for entity in entities_by_domain[MEDIA_PLAYER_DOMAIN]
        ]

        # Check if media_player entities are notification devices
        for mp in area_media_players:
            if mp in notification_devices:
                entity_ids.append(mp)

        return set(entity_ids)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""

        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug(
                "%s: Media Player restored [state=%s]", self.name, last_state.state
            )
            self._state = MediaPlayerState(last_state.state)
        else:
            self._state = MediaPlayerState.IDLE

        self.set_state()

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the state of the media player."""
        return self._state

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        return (
            MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.MEDIA_ANNOUNCE
        )

    def get_active_areas(self) -> list[str]:
        """Return area IDs that are occupied and should receive media."""
        from custom_components.magic_areas.const import ATTR_STATES

        active_area_ids = []

        # Iterate through area_data keys to get list of area IDs
        for area_id in self.areas_data:
            area_data = self.areas_data[area_id]
            area_binary_sensor_name = self._resolve_area_state_sensor(area_id)

            if not area_binary_sensor_name:
                _LOGGER.debug(
                    "%s: Area state sensor not resolved for area %s, skipping",
                    self.name,
                    area_id,
                )
                continue

            area_binary_sensor_state = self.hass.states.get(area_binary_sensor_name)
            if not area_binary_sensor_state:
                _LOGGER.debug(
                    "%s: Area state sensor '%s' not found",
                    self.name,
                    area_binary_sensor_name,
                )
                continue

            is_occupied = area_binary_sensor_state.state == STATE_ON

            # Get area states from the presence sensor attributes (ATTR_STATES = "states")
            area_states = area_binary_sensor_state.attributes.get(ATTR_STATES, [])

            # Use notification states from area's feature config
            notification_states = area_data.get("notification_states", DEFAULT_NOTIFY_STATES)

            if evaluate_area_routing(
                is_occupied=is_occupied,
                area_states=area_states,
                notification_states=notification_states,
            ):
                active_area_ids.append(area_id)

        return active_area_ids

    def update_state(self) -> None:
        """Update entity state and attributes."""
        self.update_attributes()
        self.async_write_ha_state()

    def set_state(self, state: MediaPlayerState | None = None) -> None:
        """Set the entity state."""
        if state:
            self._state = state
        self.update_state()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: object
    ) -> None:
        """Forward a piece of media to media players in active areas."""

        # Read active areas
        active_areas = self.get_active_areas()

        # Fail early
        if not active_areas:
            _LOGGER.debug("No areas active. Ignoring.")
            return

        # Gather media_player entities
        media_players: list[str] = []
        for area_id in active_areas:
            area_data = self.areas_data[area_id]
            media_players.extend(
                self.get_media_players_for_area(
                    area_data["entities_by_domain"], area_data["notification_devices"]
                )
            )

        if not media_players:
            _LOGGER.debug(
                "%s: No media_player entities to forward. Ignoring.", self.name
            )
            return

        data: dict[str, object] = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: media_players,
        }
        if kwargs:
            data.update(kwargs)

        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data
        )
