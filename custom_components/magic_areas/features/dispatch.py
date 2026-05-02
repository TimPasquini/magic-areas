"""Feature module dispatch helpers."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.components import MagicAreasConfigEntry
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.coordinator import MagicAreasCoordinator

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
        ManagedSurface,
    )
    from custom_components.magic_areas.features.registry import FeatureRegistry


type BaseEntitiesBuilder = Callable[
    [AreaConfig, MagicAreasCoordinator, MagicAreasData],
    list[Entity] | Awaitable[list[Entity]],
]


ExtraEntitiesBuilder = Callable[
    [AreaConfig, MagicAreasCoordinator, MagicAreasData],
    list[Entity] | Awaitable[list[Entity]],
]


def collect_feature_managed_surfaces(
    *,
    registry: FeatureRegistry,
    data: MagicAreasData,
    area_config: AreaConfig,
    logger: logging.Logger,
) -> list[ManagedSurface]:
    """Collect desired HA-managed surfaces from enabled feature modules."""
    surfaces: list[ManagedSurface] = []
    enabled_features = {str(feature) for feature in data.enabled_features}

    for module in registry.modules():
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
        surfaces.extend(module.desired_managed_surfaces(area_config, data))

    return surfaces


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


async def async_setup_feature_platform(
    *,
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
    domain: str,
    logger: logging.Logger,
    base_entities_builder: BaseEntitiesBuilder | None = None,
) -> None:
    """Set up a feature-backed platform with canonical dispatch/cleanup flow."""
    from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
    from custom_components.magic_areas.helpers import cleanup_removed_entries

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        logger.debug("Skipping %s setup; coordinator data unavailable", domain)
        return

    area_config = data.area_config
    coordinator = runtime_data.coordinator
    entities_to_add: list[Entity] = []

    if base_entities_builder is not None:
        base_entities = base_entities_builder(area_config, coordinator, data)
        if inspect.isawaitable(base_entities):
            entities_to_add.extend(await base_entities)
        else:
            entities_to_add.extend(base_entities)

    entities_to_add.extend(
        collect_feature_entities(
            domain=domain,
            registry=FEATURE_REGISTRY,
            data=data,
            area_config=area_config,
            coordinator=coordinator,
            logger=logger,
        )
    )

    if entities_to_add:
        async_add_entities(entities_to_add)

    if domain in data.magic_entities:
        cleanup_removed_entries(
            hass,
            entities_to_add,
            data.magic_entities[domain],
        )


__all__ = [
    "async_setup_feature_platform",
    "collect_feature_entities",
]
