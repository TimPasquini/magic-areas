"""Entity registry reference resolution for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_ble_tracker_monitor_unique_id,
    build_climate_control_switch_unique_id,
    build_cover_group_unique_id,
    build_fan_control_switch_unique_id,
    build_fan_group_id,
    build_health_sensor_unique_id,
    build_light_control_switch_unique_id,
    build_media_player_control_switch_unique_id,
    build_media_player_group_id,
    build_presence_hold_switch_unique_id,
    build_threshold_light_sensor_unique_id,
    build_wasp_sensor_unique_id,
)
from custom_components.magic_areas.core.runtime_model.identity import (
    build_presence_tracking_unique_id,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.helpers.entity_registry import EntityRegistry


@dataclass(slots=True)
class EntityReferences:
    """Resolved entity references for an area."""

    area_state_sensor: str | None = None
    presence_hold_switch: str | None = None
    light_control_switch: str | None = None
    fan_group: str | None = None
    fan_control_switch: str | None = None
    media_player_group: str | None = None
    media_player_control_switch: str | None = None
    climate_control_switch: str | None = None
    cover_group: str | None = None
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


def build_entity_references(
    area_id: str,
    entity_registry: EntityRegistry,
) -> EntityReferences:
    """Build entity references using HA entity registry lookups."""
    refs = EntityReferences()
    specs: tuple[tuple[str, str, str], ...] = (
        (
            "area_state_sensor",
            BINARY_SENSOR_DOMAIN,
            build_presence_tracking_unique_id(area_id=area_id),
        ),
        (
            "presence_hold_switch",
            SWITCH_DOMAIN,
            build_presence_hold_switch_unique_id(area_id=area_id),
        ),
        (
            "light_control_switch",
            SWITCH_DOMAIN,
            build_light_control_switch_unique_id(area_id=area_id),
        ),
        ("fan_group", FAN_DOMAIN, build_fan_group_id(area_id=area_id)),
        (
            "fan_control_switch",
            SWITCH_DOMAIN,
            build_fan_control_switch_unique_id(area_id=area_id),
        ),
        (
            "media_player_group",
            MEDIA_PLAYER_DOMAIN,
            build_media_player_group_id(area_id=area_id),
        ),
        (
            "media_player_control_switch",
            SWITCH_DOMAIN,
            build_media_player_control_switch_unique_id(area_id=area_id),
        ),
        (
            "climate_control_switch",
            SWITCH_DOMAIN,
            build_climate_control_switch_unique_id(area_id=area_id),
        ),
        ("cover_group", COVER_DOMAIN, build_cover_group_unique_id(area_id=area_id)),
        (
            "wasp_in_a_box_sensor",
            BINARY_SENSOR_DOMAIN,
            build_wasp_sensor_unique_id(area_id=area_id),
        ),
        (
            "ble_tracker_monitor",
            BINARY_SENSOR_DOMAIN,
            build_ble_tracker_monitor_unique_id(area_id=area_id),
        ),
        (
            "health_sensor",
            BINARY_SENSOR_DOMAIN,
            build_health_sensor_unique_id(area_id=area_id),
        ),
        (
            "threshold_sensor",
            BINARY_SENSOR_DOMAIN,
            build_threshold_light_sensor_unique_id(area_id=area_id),
        ),
    )

    for field_name, domain, unique_id in specs:
        setattr(
            refs,
            field_name,
            _lookup(entity_registry, domain, unique_id),
        )

    return refs


__all__ = [
    "EntityReferences",
    "build_entity_references",
]
