"""Helper for gathering entities in config flow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sun.const import DOMAIN as SUN_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.core.config import exclude_entities

CONFIG_FLOW_ENTITY_FILTER = [
    BINARY_SENSOR_DOMAIN,
    SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    INPUT_BOOLEAN_DOMAIN,
]
CONFIG_FLOW_ENTITY_FILTER_BOOL = [
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    INPUT_BOOLEAN_DOMAIN,
]
CONFIG_FLOW_ENTITY_FILTER_EXT = CONFIG_FLOW_ENTITY_FILTER + [
    LIGHT_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    CLIMATE_DOMAIN,
    SUN_DOMAIN,
    FAN_DOMAIN,
]

# Additional light tracking entities (e.g., non-device-class based)
ADDITIONAL_LIGHT_TRACKING_ENTITIES = [
    "binary_sensor.brightness",
    "binary_sensor.daylight",
    "sun.sun",
]

EntityDomainCollection = Mapping[str, Sequence[Mapping[str, str]]]


class ConfigFlowEntityGatherer:
    """Helper class for gathering entities in config flow."""

    def __init__(
        self,
        hass: HomeAssistant,
        entities_by_domain: EntityDomainCollection,
        config_entry_options: Mapping[str, object],
    ) -> None:
        """Initialize entity gatherer."""
        self.hass = hass
        self.entities_by_domain = entities_by_domain
        self.config_entry_options = config_entry_options

    @staticmethod
    def resolve_groups(raw_list: Sequence[str | list[str]]) -> list[str]:
        """Resolve entities from groups."""
        resolved_list = []
        for item in raw_list:
            if isinstance(item, list):
                for item_child in item:
                    resolved_list.append(item_child)
                continue
            resolved_list.append(item)

        return list(dict.fromkeys(resolved_list))

    def gather_all_entities(self) -> list[str]:
        """Gather all relevant entities from hass."""
        entity_registry = entityreg_async_get(self.hass)
        registry_entities = [
            entry.entity_id
            for entry in entity_registry.entities.values()
            if entry.entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
        ]
        return sorted(
            self.resolve_groups(
                [
                    entity_id
                    for entity_id in self.hass.states.async_entity_ids()
                    if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
                ]
                + registry_entities
            )
        )

    def gather_area_entities(self, all_entities: list[str]) -> list[str]:
        """Gather entities from area that exist in all_entities."""
        filtered_area_entities = []
        for domain in CONFIG_FLOW_ENTITY_FILTER_EXT:
            filtered_area_entities.extend(
                [
                    entity["entity_id"]
                    for entity in self.entities_by_domain.get(domain, [])
                    if entity["entity_id"] in all_entities
                ]
            )

        return sorted(self.resolve_groups(filtered_area_entities))

    def gather_binary_entities(self, all_entities: list[str]) -> list[str]:
        """Gather all binary entities from all_entities."""
        return sorted(
            self.resolve_groups(
                [
                    entity_id
                    for entity_id in all_entities
                    if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_BOOL
                ]
            )
        )

    def gather_combined_area_entities(
        self, area_entities: list[str]
    ) -> list[str]:
        """Gather combined area entities (area entities + excluded)."""
        return sorted(
            area_entities + exclude_entities(self.config_entry_options)
        )

    def gather_lights(self, all_entities: list[str]) -> list[str]:
        """Gather light entities from area."""
        return sorted(
            self.resolve_groups(
                [
                    entity["entity_id"]
                    for entity in self.entities_by_domain.get(LIGHT_DOMAIN, [])
                    if entity["entity_id"] in all_entities
                ]
            )
        )

    def gather_media_players(self, all_entities: list[str]) -> list[str]:
        """Gather media player entities from area."""
        return sorted(
            self.resolve_groups(
                [
                    entity["entity_id"]
                    for entity in self.entities_by_domain.get(MEDIA_PLAYER_DOMAIN, [])
                    if entity["entity_id"] in all_entities
                ]
            )
        )

    def gather_light_tracking_entities(self, all_entities: list[str]) -> list[str]:
        """Gather binary sensors with light device class for tracking."""
        eligible_light_tracking_entities = []
        for entity in all_entities:
            e_component = entity.split(".")[0]

            if e_component == BINARY_SENSOR_DOMAIN:
                entity_object = self.hass.states.get(entity)
                if not entity_object:
                    continue
                entity_object_attributes = entity_object.attributes
                if (
                    ATTR_DEVICE_CLASS in entity_object_attributes
                    and entity_object_attributes[ATTR_DEVICE_CLASS]
                    == BinarySensorDeviceClass.LIGHT
                ):
                    eligible_light_tracking_entities.append(entity)

        # Add additional entities to eligible entities
        eligible_light_tracking_entities.extend(ADDITIONAL_LIGHT_TRACKING_ENTITIES)

        return sorted(self.resolve_groups(eligible_light_tracking_entities))

    def gather_illuminance_entities(self, all_entities: list[str]) -> list[str]:
        """Gather illuminance-capable sensor entities for lux comparisons."""
        entity_registry = entityreg_async_get(self.hass)
        eligible_illuminance_entities: list[str] = []

        for entity_id in all_entities:
            if entity_id.split(".")[0] != SENSOR_DOMAIN:
                continue

            state_obj = self.hass.states.get(entity_id)
            if state_obj is not None:
                device_class = state_obj.attributes.get(ATTR_DEVICE_CLASS)
                if device_class == SensorDeviceClass.ILLUMINANCE:
                    eligible_illuminance_entities.append(entity_id)
                    continue

            entry = entity_registry.async_get(entity_id)
            if entry is None:
                continue
            if (
                entry.device_class == SensorDeviceClass.ILLUMINANCE
                or entry.original_device_class == SensorDeviceClass.ILLUMINANCE
            ):
                eligible_illuminance_entities.append(entity_id)

        return sorted(self.resolve_groups(eligible_illuminance_entities))

    def gather_all(self) -> dict[str, list[str]]:
        """Gather all entity collections at once."""
        all_entities = self.gather_all_entities()
        area_entities = self.gather_area_entities(all_entities)

        return {
            "all_entities": all_entities,
            "area_entities": area_entities,
            "all_binary_entities": self.gather_binary_entities(all_entities),
            "all_area_entities": self.gather_combined_area_entities(area_entities),
            "all_lights": self.gather_lights(all_entities),
            "all_media_players": self.gather_media_players(all_entities),
            "all_light_tracking_entities": self.gather_light_tracking_entities(
                all_entities
            ),
            "all_illuminance_entities": self.gather_illuminance_entities(all_entities),
        }
