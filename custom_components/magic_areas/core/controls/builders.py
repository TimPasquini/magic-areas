"""Shared builders for control-group feature modules."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.controls.control_group import (
    ControlGroupDefinition,
)
from custom_components.magic_areas.core.runtime_model import (
    GroupMetadataKey,
    GroupRole,
)
from custom_components.magic_areas.core.controls.registry import GroupRegistry

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

TGroupEntity = TypeVar("TGroupEntity")
EntitySnapshotDict = dict[str, str]
_EXPECTED_GROUP_BUILD_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


@dataclass(frozen=True, slots=True)
class CategorizedGroupSpec:
    """Generic category-group specification for builder helpers."""

    category: str
    members: list[str]
    trigger_states: tuple[str, ...] = ()


def build_control_group_definition(
    *,
    group_id: str,
    members: list[str],
    trigger_states: tuple[str, ...],
    policy_id: str,
    feature_id: MagicAreasFeatures,
    role: GroupRole | None = GroupRole.PRIMARY,
    metadata: Mapping[str, str] | None = None,
) -> ControlGroupDefinition:
    """Build a normalized control-group definition."""
    definition_metadata: dict[str, object] = {GroupMetadataKey.FEATURE: str(feature_id)}
    if role is not None:
        definition_metadata[GroupMetadataKey.ROLE] = str(role)
    if metadata:
        definition_metadata.update(metadata)

    return ControlGroupDefinition(
        group_id=group_id,
        members=tuple(members),
        trigger_states=trigger_states,
        policy_id=policy_id,
        metadata=definition_metadata,
    )


def register_area_default_groups(
    *,
    area_id: str,
    definitions: list[ControlGroupDefinition],
    policy_id: str,
    group_registry: GroupRegistry,
) -> None:
    """Register default control-group definitions for an area."""
    group_registry.register_area_defaults(
        area_id=area_id,
        definitions=definitions,
        policy_id=policy_id,
    )


def build_primary_group_entities(
    *,
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
    source_domain: str,
    entities_by_domain: dict[str, list[dict[str, str]]],
    feature_id: MagicAreasFeatures,
    policy_id: str,
    build_group_id: Callable[[str], str],
    group_entity_factory: Callable[[list[str]], Entity],
    trigger_states: tuple[str, ...] = (),
    control_switch_factory: Callable[[], Entity] | None = None,
    group_registry: GroupRegistry,
    logger: logging.Logger,
    group_label: str,
) -> list[Entity]:
    """Build a primary control-group entity and register its definition."""
    entities: list[Entity] = []
    definitions: list[ControlGroupDefinition] = []

    if source_domain not in entities_by_domain:
        logger.debug("%s: No %s entities for area.", area_config.name, source_domain)
    else:
        member_ids = [entity["entity_id"] for entity in entities_by_domain[source_domain]]
        if member_ids:
            try:
                entities.append(group_entity_factory(member_ids))
                definitions.append(
                    build_control_group_definition(
                        group_id=build_group_id(area_config.id),
                        members=member_ids,
                        trigger_states=trigger_states,
                        policy_id=policy_id,
                        feature_id=feature_id,
                    )
                )
            except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
                logger.exception(
                    "%s: Error creating %s: %s",
                    area_config.slug,
                    group_label,
                    str(exc),
                )

    register_area_default_groups(
        area_id=area_config.id,
        definitions=definitions,
        policy_id=policy_id,
        group_registry=group_registry,
    )

    if not area_config.is_meta() and control_switch_factory is not None:
        try:
            entities.append(control_switch_factory())
        except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
            logger.exception(
                "%s: Error loading %s control switch: %s",
                area_config.name,
                group_label,
                str(exc),
            )

    return entities


def build_partitioned_group_entities(
    *,
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
    source_domain: str,
    entities_by_domain: dict[str, list[EntitySnapshotDict]],
    partitions: list[str | None],
    partition_key: str,
    group_entity_factory: Callable[[str | None, list[EntitySnapshotDict]], Entity],
    logger: logging.Logger,
    group_label: str,
) -> list[Entity]:
    """Build grouped entities partitioned by a source attribute."""
    if source_domain not in entities_by_domain:
        logger.debug("%s: No %s entities for area.", area_config.name, source_domain)
        return []

    entities: list[Entity] = []
    for partition in partitions:
        partition_entities = [
            entity
            for entity in entities_by_domain[source_domain]
            if entity.get(partition_key) == partition
        ]
        if not partition_entities:
            continue
        try:
            entities.append(group_entity_factory(partition, partition_entities))
        except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
            logger.exception(
                "%s: Error creating %s: %s",
                area_config.slug,
                group_label,
                str(exc),
            )
    return entities


def build_control_switch_entities(
    *,
    area_config: AreaConfig,
    switch_factory: Callable[[], Entity],
    logger: logging.Logger,
    switch_label: str,
    allow_meta: bool = False,
) -> list[Entity]:
    """Build a single control switch with consistent error handling."""
    if area_config.is_meta() and not allow_meta:
        return []
    try:
        return [switch_factory()]
    except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
        logger.exception(
            "%s: Error loading %s: %s",
            area_config.name,
            switch_label,
            str(exc),
        )
        return []


def build_categorized_group_entities(
    *,
    specs: list[CategorizedGroupSpec],
    category_entity_factory: Callable[[CategorizedGroupSpec], TGroupEntity],
    category_definition_factory: Callable[[CategorizedGroupSpec], ControlGroupDefinition],
    parent_entity_factory: Callable[[list[str], list[str]], TGroupEntity],
    parent_definition_factory: Callable[[list[str], list[str]], ControlGroupDefinition],
    logger: logging.Logger,
    group_label: str,
) -> tuple[list[TGroupEntity], list[ControlGroupDefinition], list[str]]:
    """Build category groups plus a parent group from shared specs.

    Returns:
        tuple of (entities, definitions, child_categories)

    """
    entities: list[TGroupEntity] = []
    definitions: list[ControlGroupDefinition] = []
    child_categories: list[str] = []
    parent_members: list[str] = []

    for spec in specs:
        if not spec.members:
            continue

        try:
            entity = category_entity_factory(spec)
            definition = category_definition_factory(spec)
            entities.append(entity)
            definitions.append(definition)
            parent_members.extend(spec.members)
            child_categories.append(spec.category)
        except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
            logger.exception(
                "Error creating %s category group '%s': %s",
                group_label,
                spec.category,
                str(exc),
            )

    try:
        entities.append(parent_entity_factory(parent_members, child_categories))
        definitions.append(
            parent_definition_factory(parent_members, child_categories)
        )
    except _EXPECTED_GROUP_BUILD_ERRORS as exc:  # pragma: no cover
        logger.exception(
            "Error creating parent %s group: %s",
            group_label,
            str(exc),
        )

    return entities, definitions, child_categories


__all__ = [
    "CategorizedGroupSpec",
    "build_categorized_group_entities",
    "build_control_switch_entities",
    "build_control_group_definition",
    "build_partitioned_group_entities",
    "build_primary_group_entities",
    "register_area_default_groups",
]
