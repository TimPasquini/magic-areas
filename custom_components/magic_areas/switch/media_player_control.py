"""Media player control feature switch."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.controls.policies.media import (
    build_media_control_group_policy,
    MediaControlPolicy,
    MediaPolicySignals,
)
from custom_components.magic_areas.core.controls import ControlGroupContext
from custom_components.magic_areas.core.runtime_model import ControlGroupPolicyId
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import ControlSwitchBase

_LOGGER = logging.getLogger(__name__)


class MediaPlayerControlSwitch(ControlSwitchBase):
    """Switch to enable/disable climate control."""

    feature_id = MagicAreasFeatures.MEDIA_PLAYER_GROUPS
    _attr_entity_category = EntityCategory.CONFIG

    policy: MediaControlPolicy
    media_player_group_id: str | None

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Climate control switch."""

        super().__init__(area_config, coordinator)

        self.policy = build_media_control_group_policy()
        # Entity ID resolved in async_added_to_hass from coordinator snapshot
        self.media_player_group_id = None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve media player group ID from coordinator snapshot or entity registry
        entity_refs = self._entity_refs()
        if entity_refs:
            self.media_player_group_id = entity_refs.media_player_group
        if not self.media_player_group_id:
            self.media_player_group_id = self._resolve_primary_group_entity_id(
                policy_id=str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS),
                domain=MEDIA_PLAYER_DOMAIN,
            )
        self._track_area_state_with_sensor(area_state_handler=self.area_state_changed)

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        states = self._extract_relevant_area_states(
            area_id,
            states_tuple,
            require_enabled=True,
        )
        if not states:
            return

        new_states, lost_states, _current_states = states
        decision = await self._evaluate_policy(
            policy=self.policy,
            context=ControlGroupContext(
                group_id=f"media_player_groups_{self._area_id}",
                new_states=tuple(new_states),
                lost_states=tuple(lost_states),
                current_states=(),
                signals=MediaPolicySignals(
                    media_player_group_id=self.media_player_group_id
                ),
                is_enabled=bool(self.is_on),
            ),
            logger=_LOGGER,
        )
        if decision.actions:
            _LOGGER.debug("%s: Area clear, turning off media players.", self.name)
