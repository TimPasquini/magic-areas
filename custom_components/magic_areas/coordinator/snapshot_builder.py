"""Build coordinator snapshots for Magic Areas."""

from __future__ import annotations

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.area_runtime import AreaRuntime
from custom_components.magic_areas.core.config import normalize_feature_config
from custom_components.magic_areas.core.config import normalize_custom_control_groups
from custom_components.magic_areas.core.entity_ids import build_entity_references
from custom_components.magic_areas.coordinator.entity_ingestion import (
    load_area_entities,
    load_meta_area_entities,
)
from custom_components.magic_areas.coordinator.presence_ingestion import (
    build_presence_sensors,
)
from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
from custom_components.magic_areas.core.meta import (
    collect_child_areas,
    resolve_active_areas,
)
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY


async def build_snapshot(
    hass: HomeAssistant, area_config: AreaConfig, config_entry_id: str
) -> MagicAreasData:
    """Build a coordinator snapshot for the given area."""
    entities: dict[str, list[dict[str, str]]] = {}
    magic_entities: dict[str, list[dict[str, str]]] = {}
    child_areas_list: list[str] = []

    if area_config.is_meta():
        child_areas_list = collect_child_areas(
            hass,
            area_config.id,
            area_config.slug,
            area_config.floor_id,
        )
        entities, magic_entities = await load_meta_area_entities(
            hass=hass,
            child_area_slugs=child_areas_list,
            config_entry_id=config_entry_id,
            config=area_config.config,
        )
    else:
        entities, magic_entities = await load_area_entities(
            hass=hass,
            area_id=area_config.id,
            config_entry_id=config_entry_id,
            config=area_config.config,
        )

    enabled_features, feature_configs = normalize_feature_config(area_config.config)
    GROUP_REGISTRY.register_area_customs(
        area_id=area_config.id,
        definitions=normalize_custom_control_groups(area_config.config),
    )
    entity_registry = er.async_get(hass)

    entity_references = build_entity_references(
        area_id=area_config.id,
        entity_registry=entity_registry,
    )

    presence_sensors = build_presence_sensors(
        entities_by_domain=entities,
        config=area_config.config,
        slug=area_config.slug,
        enabled_features=enabled_features,
        entity_references=entity_references,
    )

    active_areas: list[str] = []
    if area_config.is_meta():
        child_presence_sensors: list[str] = []
        state_map: dict[str, str] = {}
        for child_area_id in child_areas_list:
            child_entity_id = entity_registry.async_get_entity_id(
                BINARY_SENSOR_DOMAIN,
                DOMAIN,
                f"presence_tracking_{child_area_id}_area_state",
            )
            if child_entity_id:
                child_presence_sensors.append(child_entity_id)
                area_state = hass.states.get(child_entity_id)
                if area_state:
                    state_map[child_area_id] = area_state.state
        presence_sensors = child_presence_sensors
        active_areas = resolve_active_areas(child_areas_list, state_map)

    area_runtime = AreaRuntime(last_update_success=True)

    return MagicAreasData(
        area_config=area_config,
        area_runtime=area_runtime,
        entities=entities,
        magic_entities=magic_entities,
        presence_sensors=presence_sensors,
        active_areas=active_areas,
        child_areas=child_areas_list,
        config=area_config.config,
        enabled_features=enabled_features,
        feature_configs=feature_configs,
        entity_references=entity_references,
        updated_at=dt_util.utcnow(),
    )
