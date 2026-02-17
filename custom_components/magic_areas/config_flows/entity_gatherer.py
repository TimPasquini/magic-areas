"""Helper for gathering entities in config flow."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_flow_filters import (
    CONFIG_FLOW_ENTITY_FILTER_BOOL,
    CONFIG_FLOW_ENTITY_FILTER_EXT,
)
from custom_components.magic_areas.config_keys import CONF_EXCLUDE_ENTITIES

# Additional light tracking entities (e.g., non-device-class based)
ADDITIONAL_LIGHT_TRACKING_ENTITIES = [
    "binary_sensor.brightness",
    "binary_sensor.daylight",
    "sun.sun",
]


class ConfigFlowEntityGatherer:
    """Helper class for gathering entities in config flow."""

    def __init__(
        self,
        hass: HomeAssistant,
        entities_by_domain: dict[str, list[dict[str, Any]]],
        config_entry_options: Mapping[str, Any],
    ) -> None:
        """Initialize entity gatherer."""
        self.hass = hass
        self.entities_by_domain = entities_by_domain
        self.config_entry_options = config_entry_options

    @staticmethod
    def resolve_groups(raw_list: list) -> list:
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
        return sorted(
            self.resolve_groups(
                [
                    entity_id
                    for entity_id in self.hass.states.async_entity_ids()
                    if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
                ]
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
            area_entities + self.config_entry_options.get(CONF_EXCLUDE_ENTITIES, [])
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
        }
