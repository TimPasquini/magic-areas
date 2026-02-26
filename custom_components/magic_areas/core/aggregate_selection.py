"""Aggregate selection helpers for Magic Areas."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from enum import Enum
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
)

from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_MIN_ENTITIES,
)
from custom_components.magic_areas.core.aggregate_specs import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


def _min_entities(feature_configs: dict[str, dict[str, Any]]) -> int:
    """Return minimum entities required for aggregates."""
    raw_value = feature_configs.get(MagicAreasFeatures.AGGREGATES, {}).get(
        CONF_AGGREGATES_MIN_ENTITIES,
        DEFAULT_AGGREGATES_MIN_ENTITIES,
    )
    if isinstance(raw_value, int):
        return raw_value
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return int(DEFAULT_AGGREGATES_MIN_ENTITIES)


def _is_valid_value(value: str | None) -> bool:
    """Return True when the attribute value is usable for aggregate selection."""
    if not value:
        return False
    return value not in {"None", "unknown", "unavailable"}


def _normalize_allowed_device_classes(value: Any, fallback: Sequence[str]) -> set[str]:
    """Return a normalized set of allowed device classes."""
    if not isinstance(value, (list, tuple, set)):
        return set(fallback)
    normalized: set[str] = set()
    for item in value:
        if isinstance(item, Enum):
            normalized.add(str(item.value))
        else:
            normalized.add(str(item))
    return normalized


def build_sensor_aggregates(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    feature_configs: dict[str, dict[str, Any]],
    enabled_features: set[str],
) -> list[SensorAggregateSpec]:
    """Return aggregate specs for sensor entities."""
    if MagicAreasFeatures.AGGREGATES not in enabled_features:
        return []

    if SENSOR_DOMAIN not in entities_by_domain:
        return []

    allowed_device_classes = _normalize_allowed_device_classes(
        feature_configs.get(MagicAreasFeatures.AGGREGATES, {}).get(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        ),
        DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
    )
    min_entities = _min_entities(feature_configs)

    eligible_entities: dict[str, list[str]] = {}
    unit_of_measurement_map: dict[str, list[str]] = {}

    for entity in entities_by_domain[SENSOR_DOMAIN]:
        device_class = entity.get(ATTR_DEVICE_CLASS)
        unit_of_measurement = entity.get(ATTR_UNIT_OF_MEASUREMENT)
        entity_id = entity.get(ATTR_ENTITY_ID)
        if (
            not _is_valid_value(device_class)
            or not _is_valid_value(unit_of_measurement)
            or not _is_valid_value(entity_id)
        ):
            continue
        if not isinstance(device_class, str) or not isinstance(entity_id, str):
            continue
        if not isinstance(unit_of_measurement, str):
            continue

        if device_class not in allowed_device_classes:
            continue

        eligible_entities.setdefault(device_class, []).append(entity_id)
        unit_of_measurement_map.setdefault(device_class, []).append(unit_of_measurement)

    aggregates: list[SensorAggregateSpec] = []

    for device_class, entities in eligible_entities.items():
        if len(entities) < min_entities:
            continue

        unit_of_measurements = Counter(unit_of_measurement_map[device_class])
        most_common_unit = unit_of_measurements.most_common(1)[0][0]
        aggregates.append(
            SensorAggregateSpec(
                device_class=device_class,
                entity_ids=entities,
                unit_of_measurement=most_common_unit,
            )
        )

    return aggregates


def build_binary_sensor_aggregates(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    feature_configs: dict[str, dict[str, Any]],
    enabled_features: set[str],
) -> list[BinarySensorAggregateSpec]:
    """Return aggregate specs for binary sensor entities."""
    if MagicAreasFeatures.AGGREGATES not in enabled_features:
        return []

    if BINARY_SENSOR_DOMAIN not in entities_by_domain:
        return []

    allowed_device_classes = _normalize_allowed_device_classes(
        feature_configs.get(MagicAreasFeatures.AGGREGATES, {}).get(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ),
        DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    )
    min_entities = _min_entities(feature_configs)

    device_class_entities: dict[str, list[str]] = {}

    for entity in entities_by_domain[BINARY_SENSOR_DOMAIN]:
        device_class = entity.get(ATTR_DEVICE_CLASS)
        entity_id = entity.get(ATTR_ENTITY_ID)
        if not _is_valid_value(device_class) or not _is_valid_value(entity_id):
            continue
        if not isinstance(device_class, str) or not isinstance(entity_id, str):
            continue

        if device_class not in allowed_device_classes:
            continue

        device_class_entities.setdefault(device_class, []).append(entity_id)

    aggregates: list[BinarySensorAggregateSpec] = []

    for device_class, entity_ids in device_class_entities.items():
        if len(entity_ids) < min_entities:
            continue

        aggregates.append(
            BinarySensorAggregateSpec(
                device_class=device_class,
                entity_ids=entity_ids,
            )
        )

    return aggregates


def build_health_sensor_spec(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    feature_configs: dict[str, dict[str, Any]],
    enabled_features: set[str],
) -> BinarySensorAggregateSpec | None:
    """Return an aggregate spec for health monitoring, or None if no entities match.

    Health monitoring collects all binary sensors whose device class signals
    a distress condition (e.g., gas, smoke, moisture, problem) into a single
    'problem' aggregate sensor. Unlike the regular aggregate builder, all
    matching device classes are merged into one spec rather than split by class.

    Args:
        entities_by_domain: Entity metadata grouped by domain.
        feature_configs: Per-feature configuration dict.
        enabled_features: Set of enabled feature IDs.

    Returns:
        A BinarySensorAggregateSpec with device_class 'problem', or None.

    """
    if MagicAreasFeatures.HEALTH not in enabled_features:
        return None

    if BINARY_SENSOR_DOMAIN not in entities_by_domain:
        return None

    health_device_classes = _normalize_allowed_device_classes(
        feature_configs.get(MagicAreasFeatures.HEALTH, {}).get(
            CONF_HEALTH_SENSOR_DEVICE_CLASSES,
            DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        ),
        DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
    )

    distress_entity_ids: list[str] = []

    for entity in entities_by_domain[BINARY_SENSOR_DOMAIN]:
        device_class = entity.get(ATTR_DEVICE_CLASS)
        entity_id = entity.get(ATTR_ENTITY_ID)
        if not _is_valid_value(device_class) or not _is_valid_value(entity_id):
            continue
        if not isinstance(device_class, str) or not isinstance(entity_id, str):
            continue

        if device_class not in health_device_classes:
            continue

        distress_entity_ids.append(entity_id)

    if not distress_entity_ids:
        return None

    return BinarySensorAggregateSpec(
        device_class="problem",
        entity_ids=distress_entity_ids,
    )
