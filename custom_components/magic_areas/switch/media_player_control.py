"""Media player control feature switch."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect

if TYPE_CHECKING:
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.control_group_executor import (
    execute_control_group_decision,
)
from custom_components.magic_areas.core.control_group import ControlGroupContext
from custom_components.magic_areas.core.media_control import (
    build_media_control_group_policy,
    MediaControlPolicy,
    MediaPolicySignals,
)
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_id_by_metadata,
)
from custom_components.magic_areas.core.group_contracts import ControlGroupPolicyId
from custom_components.magic_areas.core.group_metadata import GroupMetadataKey, GroupRole
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import SwitchBase

_LOGGER = logging.getLogger(__name__)


class MediaPlayerControlSwitch(SwitchBase):
    """Switch to enable/disable climate control."""

    feature_id = MagicAreasFeatures.MEDIA_PLAYER_GROUPS
    _attr_entity_category = EntityCategory.CONFIG

    policy: MediaControlPolicy
    media_player_group_id: str | None
    _listener_registry: ListenerRegistry

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Climate control switch."""

        SwitchBase.__init__(self, area_config, coordinator)

        self.policy = build_media_control_group_policy()
        # Entity ID resolved in async_added_to_hass from coordinator snapshot
        self.media_player_group_id = None
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve media player group ID from coordinator snapshot or entity registry
        if self._coordinator.data:
            self.media_player_group_id = (
                self._coordinator.data.entity_references.media_player_group
            )
        if not self.media_player_group_id:
            self.media_player_group_id = resolve_group_entity_id_by_metadata(
                self.hass,
                area_id=self._area_id,
                policy_id=str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS),
                domain=MEDIA_PLAYER_DOMAIN,
                metadata_key=str(GroupMetadataKey.ROLE),
                metadata_value=str(GroupRole.PRIMARY),
            )
        self._listener_registry.track(
            "area_state_dispatcher",
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self.area_state_changed
            ),
        )

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        if not self.is_on:
            self.logger.debug("%s: Control disabled. Skipping.", self.name)
            return

        if area_id != self._area_id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self._area_id,
            )
            return

        new_states, lost_states, _current_states = states_tuple
        if not new_states and not lost_states:
            return

        decision = self.policy.evaluate(
            ControlGroupContext(
                group_id=f"media_player_groups_{self._area_id}",
                new_states=tuple(new_states),
                lost_states=tuple(lost_states),
                current_states=(),
                signals=MediaPolicySignals(
                    media_player_group_id=self.media_player_group_id
                ),
                is_enabled=self.is_on,
            )
        )
        if decision.actions:
            _LOGGER.debug("%s: Area clear, turning off media players.", self.name)
        await execute_control_group_decision(self.hass, decision)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()
