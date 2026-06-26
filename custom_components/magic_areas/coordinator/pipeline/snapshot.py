"""Build coordinator snapshots for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import AreaConfig, AreaRuntime
from custom_components.magic_areas.core.config import (
    normalize_custom_control_groups,
    normalize_feature_config,
)
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.runtime_model import (
    EntityReferences,
    build_entity_references,
    build_presence_tracking_unique_id,
)
from custom_components.magic_areas.core.meta import (
    collect_child_areas,
    resolve_active_areas,
)
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion import (
    load_area_entities,
    load_meta_area_entities,
)
from custom_components.magic_areas.coordinator.pipeline.presence_ingestion import (
    build_presence_sensors,
)

type EntitySnapshotDict = dict[str, str]
type EntitiesByDomain = dict[str, list[EntitySnapshotDict]]
type AreaConfigDict = dict[str, object]
type FeatureConfigDict = dict[str, object]
type FeatureConfigsMap = dict[str, FeatureConfigDict]


@dataclass(slots=True)
class MagicAreasData:
    """Snapshot of area data used by platforms."""

    entities: EntitiesByDomain
    magic_entities: EntitiesByDomain
    presence_sensors: list[str]
    active_areas: list[str]
    child_areas: list[str]
    config: AreaConfigDict
    enabled_features: set[str]
    feature_configs: FeatureConfigsMap
    group_registry: GroupRegistry
    entity_references: EntityReferences
    area_config: AreaConfig
    area_runtime: AreaRuntime
    updated_at: datetime


async def build_snapshot(
    hass: HomeAssistant,
    area_config: AreaConfig,
    config_entry_id: str,
    group_registry: GroupRegistry,
) -> MagicAreasData:
    """Build a coordinator snapshot for the given area."""
    child_areas_list, entities, magic_entities = await _load_entities_for_area(
        hass=hass,
        area_config=area_config,
        config_entry_id=config_entry_id,
    )

    enabled_features, feature_configs = _resolve_feature_config(area_config=area_config)
    _register_custom_control_groups(
        area_config=area_config, group_registry=group_registry
    )
    entity_registry = er.async_get(hass)
    entity_references = _build_area_references(
        area_config=area_config, entity_registry=entity_registry
    )

    presence_sensors, active_areas = _resolve_presence_projection(
        hass=hass,
        area_config=area_config,
        entities=entities,
        enabled_features=enabled_features,
        entity_references=entity_references,
        child_areas=child_areas_list,
        entity_registry=entity_registry,
    )

    return _build_magic_areas_data(
        area_config=area_config,
        entities=entities,
        magic_entities=magic_entities,
        presence_sensors=presence_sensors,
        active_areas=active_areas,
        child_areas=child_areas_list,
        enabled_features=enabled_features,
        feature_configs=feature_configs,
        group_registry=group_registry,
        entity_references=entity_references,
    )


def _resolve_feature_config(
    *,
    area_config: AreaConfig,
) -> tuple[set[str], FeatureConfigsMap]:
    """Normalize enabled feature keys and per-feature config mapping."""
    enabled_features, feature_configs = normalize_feature_config(area_config.config)
    return enabled_features, feature_configs


def _resolve_presence_projection(
    *,
    hass: HomeAssistant,
    area_config: AreaConfig,
    entities: EntitiesByDomain,
    enabled_features: set[str],
    entity_references: EntityReferences,
    child_areas: list[str],
    entity_registry: er.EntityRegistry,
) -> tuple[list[str], list[str]]:
    """Resolve effective presence sensors and active child areas."""
    default_presence_sensors = build_presence_sensors(
        entities_by_domain=entities,
        config=area_config.config,
        slug=area_config.slug,
        enabled_features=enabled_features,
        entity_references=entity_references,
    )
    return _resolve_meta_presence_state(
        hass=hass,
        area_config=area_config,
        child_areas=child_areas,
        entity_registry=entity_registry,
        default_presence_sensors=default_presence_sensors,
    )


def _build_magic_areas_data(
    *,
    area_config: AreaConfig,
    entities: EntitiesByDomain,
    magic_entities: EntitiesByDomain,
    presence_sensors: list[str],
    active_areas: list[str],
    child_areas: list[str],
    enabled_features: set[str],
    feature_configs: FeatureConfigsMap,
    group_registry: GroupRegistry,
    entity_references: EntityReferences,
) -> MagicAreasData:
    """Shape normalized snapshot inputs into the coordinator data model."""
    area_runtime = AreaRuntime(last_update_success=True)
    return MagicAreasData(
        area_config=area_config,
        area_runtime=area_runtime,
        entities=entities,
        magic_entities=magic_entities,
        presence_sensors=presence_sensors,
        active_areas=active_areas,
        child_areas=child_areas,
        config=area_config.config,
        enabled_features=enabled_features,
        feature_configs=feature_configs,
        group_registry=group_registry,
        entity_references=entity_references,
        updated_at=dt_util.utcnow(),
    )


async def _load_entities_for_area(
    *,
    hass: HomeAssistant,
    area_config: AreaConfig,
    config_entry_id: str,
) -> tuple[list[str], EntitiesByDomain, EntitiesByDomain]:
    """Load area/meta entities and return child areas when applicable."""
    if area_config.is_meta():
        child_areas = collect_child_areas(
            hass,
            area_config.id,
            area_config.slug,
            area_config.floor_id,
        )
        entities, magic_entities = await load_meta_area_entities(
            hass=hass,
            child_area_slugs=child_areas,
            config_entry_id=config_entry_id,
            config=area_config.config,
        )
        return child_areas, entities, magic_entities

    entities, magic_entities = await load_area_entities(
        hass=hass,
        area_id=area_config.id,
        config_entry_id=config_entry_id,
        config=area_config.config,
    )
    return [], entities, magic_entities


def _register_custom_control_groups(
    *,
    area_config: AreaConfig,
    group_registry: GroupRegistry,
) -> None:
    """Register normalized custom control group definitions for an area."""
    group_registry.register_area_customs(
        area_id=area_config.id,
        definitions=normalize_custom_control_groups(area_config.config),
    )


def _build_area_references(
    *,
    area_config: AreaConfig,
    entity_registry: er.EntityRegistry,
) -> EntityReferences:
    """Resolve all area-scoped runtime entity references."""
    return build_entity_references(
        area_id=area_config.id,
        entity_registry=entity_registry,
    )


def _resolve_meta_presence_state(
    *,
    hass: HomeAssistant,
    area_config: AreaConfig,
    child_areas: list[str],
    entity_registry: er.EntityRegistry,
    default_presence_sensors: list[str],
) -> tuple[list[str], list[str]]:
    """Resolve effective presence sensors and active areas for meta snapshots."""
    if not area_config.is_meta():
        return default_presence_sensors, []

    child_presence_sensors: list[str] = []
    state_map: dict[str, str] = {}
    for child_area_id in child_areas:
        child_entity_id = entity_registry.async_get_entity_id(
            BINARY_SENSOR_DOMAIN,
            DOMAIN,
            build_presence_tracking_unique_id(area_id=child_area_id),
        )
        if child_entity_id is None:
            continue
        child_presence_sensors.append(child_entity_id)
        area_state = hass.states.get(child_entity_id)
        if area_state is not None:
            state_map[child_area_id] = area_state.state

    return child_presence_sensors, resolve_active_areas(child_areas, state_map)
