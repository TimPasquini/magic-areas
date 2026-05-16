"""Light group entity implementations for Magic Areas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.group.light import FORWARDED_ATTRIBUTES, LightGroup
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_ON
from homeassistant.core import Context
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

GROUP_DOMAIN = "group"


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
            key: value for key, value in kwargs.items() if key in FORWARDED_ATTRIBUTES
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


__all__ = ["MagicLightGroup"]
