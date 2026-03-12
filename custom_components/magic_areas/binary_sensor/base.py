"""Base classes for binary sensor component."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup

from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.policy import AGGREGATE_MODE_ALL

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class AreaSensorGroupBinarySensor(MagicGroupEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        device_class: str,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicGroupEntity.__init__(
            self,
            area_config=area_config,
            coordinator=coordinator,
            domain=BINARY_SENSOR_DOMAIN,
            member_entity_ids=entity_ids,
            translation_key=device_class,
        )
        BinarySensorGroup.__init__(
            self,
            device_class=(
                BinarySensorDeviceClass(device_class) if device_class else None
            ),
            name="",
            unique_id=self._attr_unique_id,
            entity_ids=self.member_entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
        )
        delattr(self, "_attr_name")
