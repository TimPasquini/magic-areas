"""Feature module dispatch helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.features.registry import FeatureRegistry


def collect_feature_entities(
    *,
    domain: str,
    registry: FeatureRegistry,
    data: MagicAreasData,
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
    logger: logging.Logger,
) -> list[Entity]:
    """Collect entities from feature modules for a platform domain."""
    entities: list[Entity] = []
    registry.validate_dependencies(data)
    enabled_features = {str(feature) for feature in data.enabled_features}

    for module in registry.modules_for_domain(domain):
        if not module.is_enabled(data):
            continue
        missing = {feature.value for feature in module.depends_on()} - enabled_features
        if missing:
            logger.warning(
                "Feature %s missing dependencies: %s",
                module.id,
                ", ".join(sorted(missing)),
            )
            continue
        module_entities = module.build_entities(area_config, coordinator, data)
        domain_entities = [
            entity
            for entity in module_entities
            if getattr(entity, "entity_id", "").startswith(f"{domain}.")
        ]
        if domain_entities:
            entities.extend(domain_entities)
            module.attach_listeners(domain_entities, data)

    return entities


__all__ = ["collect_feature_entities"]
