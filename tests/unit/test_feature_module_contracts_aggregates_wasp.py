"""Contract tests for aggregate and wasp feature modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.sensor import (
    create_aggregate_sensors_from_definitions as create_sensor_aggregates,
)
from custom_components.magic_areas.binary_sensor import (
    create_aggregate_sensors_from_definitions as create_binary_aggregates,
    create_illuminance_threshold,
    create_wasp_in_a_box_sensor,
)

from .feature_module_contracts_testkit import (
    build_aggregate_definitions,
    get_module,
    make_area_config,
    make_coordinator,
    make_snapshot,
)


def test_aggregates_module_matches_legacy_sensor_entities() -> None:
    """Aggregates module should match legacy sensor aggregate output."""
    area_config = make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                ATTR_ENTITY_ID: "sensor.temp_1",
                ATTR_UNIT_OF_MEASUREMENT: "°C",
            },
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                ATTR_ENTITY_ID: "sensor.temp_2",
                ATTR_UNIT_OF_MEASUREMENT: "°C",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.TEMPERATURE],
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = make_coordinator(snapshot)
    definitions = build_aggregate_definitions(snapshot)

    legacy_entities = create_sensor_aggregates(
        definitions=definitions,
        area_config=area_config,
        coordinator=coordinator,
    )

    module = get_module("aggregates")
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    legacy_ids = sorted(entity.entity_id for entity in legacy_entities)
    module_ids = sorted(
        entity.entity_id for entity in module_entities if entity.entity_id.startswith("sensor.")
    )
    assert module_ids == legacy_ids


@pytest.mark.asyncio
async def test_aggregates_module_matches_legacy_binary_entities_and_threshold(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aggregates module should match legacy binary aggregates and threshold output."""
    area_config = make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                ATTR_ENTITY_ID: "sensor.lux_1",
                ATTR_UNIT_OF_MEASUREMENT: "lx",
            },
        ],
        BINARY_SENSOR_DOMAIN: [
            {ATTR_DEVICE_CLASS: "motion", ATTR_ENTITY_ID: "binary_sensor.motion_1"},
            {ATTR_DEVICE_CLASS: "motion", ATTR_ENTITY_ID: "binary_sensor.motion_2"},
        ],
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.ILLUMINANCE],
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 50,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: 10,
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.aggregates.runtime.resolve_aggregate_entity_id",
        MagicMock(
            return_value=(
                "sensor.magic_areas_aggregates_kitchen_aggregate_illuminance"
            )
        ),
    )
    coordinator = make_coordinator(snapshot, hass)
    definitions = build_aggregate_definitions(snapshot)

    legacy_entities = create_binary_aggregates(
        definitions=definitions,
        area_config=area_config,
        coordinator=coordinator,
    )
    threshold_entity = create_illuminance_threshold(hass, snapshot, area_config, coordinator)
    if threshold_entity:
        legacy_entities.append(threshold_entity)

    module = get_module("aggregates")
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    legacy_ids = sorted(entity.entity_id for entity in legacy_entities)
    module_ids = sorted(
        entity.entity_id
        for entity in module_entities
        if entity.entity_id.startswith("binary_sensor.")
    )
    assert module_ids == legacy_ids


def test_aggregates_module_respects_min_entities_config() -> None:
    """Aggregates module should respect min-entities config like legacy."""
    area_config = make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                ATTR_ENTITY_ID: "sensor.temp_1",
                ATTR_UNIT_OF_MEASUREMENT: "°C",
            }
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.TEMPERATURE],
            CONF_AGGREGATES_MIN_ENTITIES: 2,
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = make_coordinator(snapshot)
    definitions = build_aggregate_definitions(snapshot)

    legacy_entities = create_sensor_aggregates(
        definitions=definitions,
        area_config=area_config,
        coordinator=coordinator,
    )

    module = get_module("aggregates")
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    assert legacy_entities == []
    assert module_entities == []


def test_aggregates_module_registers_group_registry_definitions() -> None:
    """Aggregates module should register canonical aggregate definitions in group registry."""
    area_config = make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                ATTR_ENTITY_ID: "sensor.temp_1",
                ATTR_UNIT_OF_MEASUREMENT: "°C",
            },
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                ATTR_ENTITY_ID: "sensor.temp_2",
                ATTR_UNIT_OF_MEASUREMENT: "°C",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.TEMPERATURE],
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("aggregates")

    with patch(
        "custom_components.magic_areas.features.modules.aggregates.register_aggregate_definitions"
    ) as register_defs:
        module.build_entities(area_config, coordinator, snapshot)

    register_defs.assert_called_once()
    _, kwargs = register_defs.call_args
    assert kwargs["area_id"] == area_config.id
    assert any(
        definition.domain == SENSOR_DOMAIN
        and definition.device_class == SensorDeviceClass.TEMPERATURE
        for definition in kwargs["definitions"]
    )


def test_aggregates_module_registers_health_definition_without_creating_health_aggregate_entity() -> None:
    """Aggregates module registers health definitions without creating health aggregate entities."""
    area_config = make_area_config()
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {ATTR_DEVICE_CLASS: "smoke", ATTR_ENTITY_ID: "binary_sensor.smoke_1"},
            {ATTR_DEVICE_CLASS: "smoke", ATTR_ENTITY_ID: "binary_sensor.smoke_2"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        },
        MagicAreasFeatures.HEALTH: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke"],
        },
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.HEALTH},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("aggregates")

    with patch(
        "custom_components.magic_areas.features.modules.aggregates.register_aggregate_definitions"
    ) as register_defs:
        module_entities = module.build_entities(area_config, coordinator, snapshot)

    _, kwargs = register_defs.call_args
    assert any(
        definition.domain == BINARY_SENSOR_DOMAIN and definition.device_class == "problem"
        for definition in kwargs["definitions"]
    )
    assert all(
        "_aggregate_problem" not in entity.entity_id
        for entity in module_entities
        if getattr(entity, "entity_id", None)
    )


def test_wasp_module_matches_legacy_entities_and_config() -> None:
    """Wasp module should match legacy output and config usage."""
    area_config = make_area_config()
    feature_configs = {
        MagicAreasFeatures.WASP_IN_A_BOX: {
            CONF_WASP_IN_A_BOX_DELAY: 3,
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 7,
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES: ["motion"],
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.WASP_IN_A_BOX},
        feature_configs=feature_configs,
        entities={},
    )
    coordinator = make_coordinator(snapshot)

    legacy_entities = create_wasp_in_a_box_sensor(snapshot, area_config, coordinator)

    module = get_module("wasp_in_a_box")
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    legacy_ids = sorted(entity.entity_id for entity in legacy_entities)
    module_ids = sorted(entity.entity_id for entity in module_entities)
    assert module_ids == legacy_ids

    assert module_entities
    entity = module_entities[0]
    assert getattr(entity, "_delay", None) == 3
    assert getattr(entity, "_wasp_timeout", None) == 7


def test_wasp_module_disabled_without_aggregates() -> None:
    """Wasp module should be disabled when aggregates dependency is missing."""
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.WASP_IN_A_BOX},
        feature_configs={},
        entities={},
    )
    module = get_module("wasp_in_a_box")

    assert module.is_enabled(snapshot) is False


def test_aggregates_module_does_not_attach_listeners() -> None:
    """Aggregates module should not attach extra listeners."""
    module = get_module("aggregates")

    with (
        patch("homeassistant.helpers.dispatcher.async_dispatcher_connect") as dispatcher_connect,
        patch("homeassistant.helpers.event.async_track_state_change_event") as track_state_change,
    ):
        module.attach_listeners([], MagicMock())

    dispatcher_connect.assert_not_called()
    track_state_change.assert_not_called()


def test_wasp_module_does_not_attach_listeners() -> None:
    """Wasp module should not attach extra listeners."""
    module = get_module("wasp_in_a_box")

    with (
        patch("homeassistant.helpers.dispatcher.async_dispatcher_connect") as dispatcher_connect,
        patch("homeassistant.helpers.event.async_track_state_change_event") as track_state_change,
    ):
        module.attach_listeners([], MagicMock())

    dispatcher_connect.assert_not_called()
    track_state_change.assert_not_called()
