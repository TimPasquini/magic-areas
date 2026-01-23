"""Cover controls for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.cover import (
    DEVICE_CLASSES as COVER_DEVICE_CLASSES,
    CoverDeviceClass,
)
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.group.cover import CoverGroup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.config_keys import (
    EMPTY_STRING,
)
from custom_components.magic_areas.features import CONF_FEATURE_COVER_GROUPS
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoCoverGroups,
)
from custom_components.magic_areas.util import cleanup_removed_entries

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area cover config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping cover setup; coordinator data unavailable")
        return
    area: MagicArea = data.area

    # Check feature availability
    if CONF_FEATURE_COVER_GROUPS not in data.enabled_features:
        return

    # Check if there are any covers
    if COVER_DOMAIN not in data.entities:
        _LOGGER.debug("No %s entities for area %s", COVER_DOMAIN, area.name)
        return

    entities_to_add = []

    # Append None to the list of device classes to catch those covers that
    # don't have a device class assigned (and put them in their own group)
    for device_class in [*COVER_DEVICE_CLASSES, None]:
        entities_in_device_class = [
            e
            for e in data.entities[COVER_DOMAIN]
            if e.get("device_class") == device_class
        ]
        cover_ids = [e["entity_id"] for e in entities_in_device_class]

        if any(cover_ids):
            _LOGGER.debug(
                "Creating %s cover group for %s with covers: %s",
                device_class,
                area.name,
                cover_ids,
            )
            entities_to_add.append(
                AreaCoverGroup(area, device_class, entities_in_device_class)
            )

    if entities_to_add:
        async_add_entities(entities_to_add)

    if COVER_DOMAIN in data.magic_entities:
        cleanup_removed_entries(
            area.hass, entities_to_add, data.magic_entities[COVER_DOMAIN]
        )


class AreaCoverGroup(MagicEntity, CoverGroup):
    """Cover group for handling all the covers in the area."""

    feature_info = MagicAreasFeatureInfoCoverGroups()

    def __init__(
        self,
        area: MagicArea,
        device_class: str | None,
        entities: list[dict[str, str]],
    ) -> None:
        """Initialize the cover group."""
        MagicEntity.__init__(
            self, area, domain=COVER_DOMAIN, translation_key=device_class
        )
        sensor_device_class: CoverDeviceClass | None = (
            CoverDeviceClass(device_class) if device_class else None
        )
        self._attr_device_class = sensor_device_class
        self._entities = entities
        CoverGroup.__init__(
            self,
            entities=[e["entity_id"] for e in self._entities],
            name=EMPTY_STRING,
            unique_id=self._attr_unique_id,
        )
        delattr(self, "_attr_name")
