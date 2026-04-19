"""Coordinator pipeline public API."""

from custom_components.magic_areas.coordinator.pipeline.entity_ingestion import (
    EntitySnapshot,
    build_entity_dict,
    filter_entity_list,
    group_entities,
    is_magic_area_entity,
    load_area_entities,
    load_meta_area_entities,
    should_exclude_entity,
)
from custom_components.magic_areas.coordinator.pipeline.lifecycle import (
    MetaAreaReloadManager,
    make_device_registry_filter,
    make_entity_registry_filter,
    attach_registry_listeners,
)
from custom_components.magic_areas.coordinator.pipeline.presence_ingestion import (
    build_presence_sensors,
)
from custom_components.magic_areas.coordinator.pipeline.snapshot import (
    MagicAreasData,
    build_snapshot,
)

__all__ = [
    "EntitySnapshot",
    "MagicAreasData",
    "MetaAreaReloadManager",
    "build_entity_dict",
    "build_presence_sensors",
    "attach_registry_listeners",
    "build_snapshot",
    "filter_entity_list",
    "group_entities",
    "is_magic_area_entity",
    "load_area_entities",
    "load_meta_area_entities",
    "make_device_registry_filter",
    "make_entity_registry_filter",
    "should_exclude_entity",
]
