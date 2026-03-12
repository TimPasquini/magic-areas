"""Entity ID resolution for Magic Areas.

Uses Home Assistant's entity registry to resolve entity IDs by unique_id.
All platforms should use these helpers instead of hardcoding entity ID construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.group_contracts import (
    ControlGroupPolicyId,
    build_fan_group_id,
    build_media_player_group_id,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.helpers.entity_registry import EntityRegistry


@dataclass(slots=True)
class EntityReferences:
    """Resolved entity references for an area.

    All fields are resolved from the HA entity registry by unique_id.
    None means the entity does not exist in the registry.
    """

    # Presence tracking
    area_state_sensor: str | None = None
    presence_hold_switch: str | None = None

    # Aggregates (by device class)
    aggregates_by_device_class: dict[str, str] = field(default_factory=dict)
    binary_aggregates_by_device_class: dict[str, str] = field(default_factory=dict)

    # Light groups
    light_control_switch: str | None = None
    light_groups_by_category: dict[str, str] = field(default_factory=dict)

    # Fan groups
    fan_group: str | None = None
    fan_control_switch: str | None = None

    # Media player groups
    media_player_group: str | None = None
    media_player_control_switch: str | None = None

    # Climate control
    climate_control_switch: str | None = None

    # Cover groups
    cover_group: str | None = None

    # Other sensors
    wasp_in_a_box_sensor: str | None = None
    ble_tracker_monitor: str | None = None
    threshold_sensor: str | None = None
    health_sensor: str | None = None


def _lookup(
    entity_registry: EntityRegistry,
    ha_domain: str,
    unique_id: str,
) -> str | None:
    """Look up entity_id from the HA entity registry by unique_id."""
    return entity_registry.async_get_entity_id(ha_domain, DOMAIN, unique_id)


# Unique ID prefix constants (match feature_info.id values)
_AGGREGATES_PREFIX = "aggregates"


def build_entity_references(
    area_id: str,
    entity_registry: EntityRegistry,
) -> EntityReferences:
    """Build entity references using HA entity registry lookups.

    Resolves entity IDs by unique_id, which is stable and survives entity renames.

    Args:
        area_id: The area ID (stable identifier)
        entity_registry: Home Assistant's entity registry

    Returns:
        EntityReferences with resolved entity IDs (None for missing entities)

    """
    refs = EntityReferences()

    # --- Fixed entities (known unique_ids) ---

    # Presence tracking
    refs.area_state_sensor = _lookup(
        entity_registry,
        BINARY_SENSOR_DOMAIN,
        f"presence_tracking_{area_id}_area_state",
    )
    refs.presence_hold_switch = _lookup(
        entity_registry,
        SWITCH_DOMAIN,
        f"presence_hold_{area_id}",
    )

    # Light groups
    refs.light_control_switch = _lookup(
        entity_registry,
        SWITCH_DOMAIN,
        f"light_groups_{area_id}_light_control",
    )

    # Fan groups
    refs.fan_group = _lookup(
        entity_registry,
        FAN_DOMAIN,
        build_fan_group_id(area_id=area_id),
    )
    refs.fan_control_switch = _lookup(
        entity_registry,
        SWITCH_DOMAIN,
        f"fan_groups_{area_id}_fan_control",
    )

    # Media player groups
    refs.media_player_group = _lookup(
        entity_registry,
        MEDIA_PLAYER_DOMAIN,
        build_media_player_group_id(area_id=area_id),
    )
    refs.media_player_control_switch = _lookup(
        entity_registry,
        SWITCH_DOMAIN,
        f"media_player_groups_{area_id}_media_player_control",
    )

    # Climate control (translation_key == feature_info.id, so no suffix)
    refs.climate_control_switch = _lookup(
        entity_registry,
        SWITCH_DOMAIN,
        f"climate_control_{area_id}",
    )

    # Cover groups
    refs.cover_group = _lookup(
        entity_registry,
        COVER_DOMAIN,
        f"cover_groups_{area_id}_cover_group",
    )

    # Other sensors
    # wasp_in_a_box: translation_key == feature_info.id, so no suffix
    refs.wasp_in_a_box_sensor = _lookup(
        entity_registry,
        BINARY_SENSOR_DOMAIN,
        f"wasp_in_a_box_{area_id}",
    )
    refs.ble_tracker_monitor = _lookup(
        entity_registry,
        BINARY_SENSOR_DOMAIN,
        f"ble_trackers_{area_id}_ble_tracker_monitor",
    )
    # health: translation_key == feature_info.id, so no suffix
    refs.health_sensor = _lookup(
        entity_registry,
        BINARY_SENSOR_DOMAIN,
        f"health_{area_id}",
    )

    # --- Dynamic entities (iterate registry for aggregates, light categories) ---

    # Aggregate unique_ids: aggregates_{area_id}_aggregate_{device_class}
    aggregate_sensor_prefix = f"{_AGGREGATES_PREFIX}_{area_id}_aggregate_"

    # Light group unique_ids: light_groups_{area_id}_{category}
    light_group_prefix = f"{ControlGroupPolicyId.LIGHT_GROUPS}_{area_id}_"

    # Threshold unique_ids: threshold_{area_id}_{device_class}
    threshold_prefix = f"threshold_{area_id}_"

    for entry in entity_registry.entities.values():
        if entry.platform != DOMAIN:
            continue

        uid = entry.unique_id

        # Sensor aggregates
        if entry.domain == SENSOR_DOMAIN and uid.startswith(aggregate_sensor_prefix):
            device_class = uid[len(aggregate_sensor_prefix) :]
            refs.aggregates_by_device_class[device_class] = entry.entity_id

        # Binary sensor aggregates
        elif entry.domain == BINARY_SENSOR_DOMAIN and uid.startswith(
            aggregate_sensor_prefix
        ):
            device_class = uid[len(aggregate_sensor_prefix) :]
            refs.binary_aggregates_by_device_class[device_class] = entry.entity_id

        # Light groups by category
        elif entry.domain == LIGHT_DOMAIN and uid.startswith(light_group_prefix):
            category = uid[len(light_group_prefix) :]
            refs.light_groups_by_category[category] = entry.entity_id

        # Threshold sensors (by device class)
        elif entry.domain == BINARY_SENSOR_DOMAIN and uid.startswith(threshold_prefix):
            # Use the first threshold sensor found for this area
            if not refs.threshold_sensor:
                refs.threshold_sensor = entry.entity_id

    return refs
