"""Pure presence selection helpers for Magic Areas."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from custom_components.magic_areas.config_keys import (
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_WASP_IN_A_BOX,
)
from custom_components.magic_areas.ha_domains import (
    BINARY_SENSOR_DOMAIN,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

if TYPE_CHECKING:
    from custom_components.magic_areas.core.entity_ids import EntityReferences


def build_presence_sensors(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    config: dict[str, Any],
    slug: str,
    enabled_features: set[str],
    entity_references: EntityReferences | None = None,
) -> list[str]:
    """Return list of entity ids used for presence tracking."""
    sensors: list[str] = []

    valid_presence_platforms = config.get(
        CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS
    )
    allowed_device_classes = [
        dc.value if isinstance(dc, Enum) else dc
        for dc in config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS, [])
    ]

    for component, entities in entities_by_domain.items():
        if component not in valid_presence_platforms:
            continue

        for entity in entities:
            if not entity:
                continue

            if component == BINARY_SENSOR_DOMAIN:
                if ATTR_DEVICE_CLASS not in entity:
                    continue

                if entity[ATTR_DEVICE_CLASS] not in allowed_device_classes:
                    continue

            sensors.append(entity[ATTR_ENTITY_ID])

    # Resolve magic_areas-generated presence sensors from entity references
    if CONF_FEATURE_PRESENCE_HOLD in enabled_features:
        if entity_references and entity_references.presence_hold_switch:
            sensors.append(entity_references.presence_hold_switch)

    if CONF_FEATURE_BLE_TRACKERS in enabled_features:
        if entity_references and entity_references.ble_tracker_monitor:
            sensors.append(entity_references.ble_tracker_monitor)

    if (
        CONF_FEATURE_AGGREGATION in enabled_features
        and CONF_FEATURE_WASP_IN_A_BOX in enabled_features
    ):
        if entity_references and entity_references.wasp_in_a_box_sensor:
            sensors.append(entity_references.wasp_in_a_box_sensor)

    return sensors
