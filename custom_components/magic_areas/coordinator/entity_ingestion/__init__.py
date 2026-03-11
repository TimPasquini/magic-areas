"""Entity loading package public API."""

from custom_components.magic_areas.coordinator.entity_ingestion.loader import (
    load_area_entities,
    load_meta_area_entities,
)
from custom_components.magic_areas.coordinator.entity_ingestion.registry_queries import (
    get_device_registry,
    get_entity_registry,
)

__all__ = [
    "get_device_registry",
    "get_entity_registry",
    "load_area_entities",
    "load_meta_area_entities",
]
