"""Fan groups & control for Magic Areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.group.fan import FanGroup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.core_constants import (
    EMPTY_STRING,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_FAN_GROUPS,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoFanGroups,
)
from custom_components.magic_areas.util import cleanup_removed_entries

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping fan setup; coordinator data unavailable")
        return
    area: MagicArea = data.area

    # Check feature availability
    if CONF_FEATURE_FAN_GROUPS not in data.enabled_features:
        return

    # Check if there are any fan entities
    if FAN_DOMAIN not in data.entities:
        _LOGGER.debug("%s: No %s entities for area.", area.name, FAN_DOMAIN)
        return

    fan_entities: list[str] = [e["entity_id"] for e in data.entities[FAN_DOMAIN]]

    fan_groups: list[AreaFanGroup] = []
    try:
        fan_groups = [AreaFanGroup(area, fan_entities)]
        if fan_groups:
            async_add_entities(fan_groups)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating fan group: %s",
            area.slug,
            str(e),
        )

    if FAN_DOMAIN in data.magic_entities:
        cleanup_removed_entries(area.hass, fan_groups, data.magic_entities[FAN_DOMAIN])


class AreaFanGroup(MagicEntity, FanGroup):
    """Fan Group."""

    feature_info = MagicAreasFeatureInfoFanGroups()

    def __init__(self, area: MagicArea, entities: list[str]) -> None:
        """Init the fan group for the area."""
        MagicEntity.__init__(self, area=area, domain=FAN_DOMAIN)
        FanGroup.__init__(
            self,
            entities=entities,
            name=EMPTY_STRING,
            unique_id=self.unique_id,
        )

        delattr(self, "_attr_name")
