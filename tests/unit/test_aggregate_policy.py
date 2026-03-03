"""Tests for canonical aggregate selection policy."""

from typing import Any

from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.core.aggregate_policy import (
    AggregateKind,
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.core.aggregate_selection import (
    build_binary_sensor_aggregates,
    build_health_sensor_spec,
    build_sensor_aggregates,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


def test_default_policy_sensor_specs() -> None:
    """Default aggregate policy should produce sensor aggregate specs."""
    policy = build_default_aggregate_selection_policy()
    context = AggregatePolicyContext(
        entities_by_domain={
            "sensor": [
                {
                    "entity_id": "sensor.room_temp_1",
                    "device_class": "temperature",
                    "unit_of_measurement": "C",
                },
                {
                    "entity_id": "sensor.room_temp_2",
                    "device_class": "temperature",
                    "unit_of_measurement": "C",
                },
            ]
        },
        feature_configs={
            MagicAreasFeatures.AGGREGATES: {
                CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
                CONF_AGGREGATES_MIN_ENTITIES: 2,
            }
        },
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )

    specs = policy.sensor_specs(context)
    assert len(specs) == 1
    assert specs[0].device_class == "temperature"
    assert len(specs[0].entity_ids) == 2


def test_default_policy_binary_and_health_specs() -> None:
    """Default aggregate policy should produce binary aggregate and health specs."""
    policy = build_default_aggregate_selection_policy()
    context = AggregatePolicyContext(
        entities_by_domain={
            "binary_sensor": [
                {
                    "entity_id": "binary_sensor.motion_1",
                    "device_class": "motion",
                },
                {
                    "entity_id": "binary_sensor.motion_2",
                    "device_class": "motion",
                },
                {
                    "entity_id": "binary_sensor.smoke_1",
                    "device_class": "smoke",
                },
            ]
        },
        feature_configs={
            MagicAreasFeatures.AGGREGATES: {
                CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
                CONF_AGGREGATES_MIN_ENTITIES: 2,
            },
            MagicAreasFeatures.HEALTH: {
                CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke"],
            },
        },
        enabled_features={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.HEALTH},
    )

    binary_specs = policy.binary_sensor_specs(context)
    assert len(binary_specs) == 1
    assert binary_specs[0].device_class == "motion"
    assert len(binary_specs[0].entity_ids) == 2

    health_spec = policy.health_spec(context)
    assert health_spec is not None
    assert health_spec.device_class == "problem"
    assert health_spec.entity_ids == ["binary_sensor.smoke_1"]


def test_default_policy_returns_unified_aggregate_definitions() -> None:
    """Default aggregate policy should expose unified aggregate definitions."""
    policy = build_default_aggregate_selection_policy()
    context = AggregatePolicyContext(
        entities_by_domain={
            "sensor": [
                {
                    "entity_id": "sensor.room_temp_1",
                    "device_class": "temperature",
                    "unit_of_measurement": "C",
                },
                {
                    "entity_id": "sensor.room_temp_2",
                    "device_class": "temperature",
                    "unit_of_measurement": "C",
                },
            ],
            "binary_sensor": [
                {"entity_id": "binary_sensor.motion_1", "device_class": "motion"},
                {"entity_id": "binary_sensor.motion_2", "device_class": "motion"},
                {"entity_id": "binary_sensor.smoke_1", "device_class": "smoke"},
            ],
        },
        feature_configs={
            MagicAreasFeatures.AGGREGATES: {
                CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
                CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
                CONF_AGGREGATES_MIN_ENTITIES: 2,
            },
            MagicAreasFeatures.HEALTH: {
                CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke"],
            },
        },
        enabled_features={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.HEALTH},
    )

    definitions = policy.aggregate_definitions(context)
    assert len(definitions) == 3

    by_key = {(definition.domain, definition.device_class): definition for definition in definitions}
    sensor_def = by_key[("sensor", "temperature")]
    assert sensor_def.unit_of_measurement == "C"
    assert sensor_def.kind is AggregateKind.STANDARD

    binary_def = by_key[("binary_sensor", "motion")]
    assert binary_def.kind is AggregateKind.STANDARD
    assert len(binary_def.entity_ids) == 2

    health_def = by_key[("binary_sensor", "problem")]
    assert health_def.kind is AggregateKind.HEALTH
    assert health_def.entity_ids == ("binary_sensor.smoke_1",)


def test_default_policy_matches_existing_selection_helpers() -> None:
    """Default aggregate policy should remain parity-equal to selection helpers."""
    entities_by_domain = {
        "sensor": [
            {
                "entity_id": "sensor.room_temp_1",
                "device_class": "temperature",
                "unit_of_measurement": "C",
            },
            {
                "entity_id": "sensor.room_temp_2",
                "device_class": "temperature",
                "unit_of_measurement": "C",
            },
        ],
        "binary_sensor": [
            {
                "entity_id": "binary_sensor.motion_1",
                "device_class": "motion",
            },
            {
                "entity_id": "binary_sensor.motion_2",
                "device_class": "motion",
            },
            {
                "entity_id": "binary_sensor.smoke_1",
                "device_class": "smoke",
            },
        ],
    }
    feature_configs: dict[str | MagicAreasFeatures, dict[str, Any]] = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
            CONF_AGGREGATES_MIN_ENTITIES: 2,
        },
        MagicAreasFeatures.HEALTH: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke"],
        },
    }
    enabled_features = {MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.HEALTH}

    context = AggregatePolicyContext(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features=enabled_features,
    )
    policy = build_default_aggregate_selection_policy()

    assert policy.sensor_specs(context) == build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features=enabled_features,
    )
    assert policy.binary_sensor_specs(context) == build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features=enabled_features,
    )
    assert policy.health_spec(context) == build_health_sensor_spec(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features=enabled_features,
    )
