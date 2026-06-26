"""Presence sensor ingestion for coordinator snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

from custom_components.magic_areas.components import BINARY_SENSOR_DOMAIN
from custom_components.magic_areas.core.config import (
    presence_device_platforms,
    presence_sensor_device_classes,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import EntityReferences


def build_presence_sensors(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    config: Mapping[str, object],
    slug: str,
    enabled_features: set[str],
    entity_references: EntityReferences | None = None,
) -> list[str]:
    """Return list of entity ids used for presence tracking."""
    del slug
    sensors: list[str] = []

    valid_presence_platforms = presence_device_platforms(config)
    allowed_device_classes = presence_sensor_device_classes(config)

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

    if MagicAreasFeatures.PRESENCE_HOLD in enabled_features:
        if entity_references and entity_references.presence_hold_switch:
            sensors.append(entity_references.presence_hold_switch)

    if MagicAreasFeatures.BLE_TRACKER in enabled_features:
        if entity_references and entity_references.ble_tracker_monitor:
            sensors.append(entity_references.ble_tracker_monitor)

    if (
        MagicAreasFeatures.AGGREGATES in enabled_features
        and MagicAreasFeatures.WASP_IN_A_BOX in enabled_features
    ):
        if entity_references and entity_references.wasp_in_a_box_sensor:
            sensors.append(entity_references.wasp_in_a_box_sensor)

    return sensors


__all__ = ["build_presence_sensors"]
