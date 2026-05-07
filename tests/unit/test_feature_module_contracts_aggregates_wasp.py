"""Contract tests for aggregate and wasp feature modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT

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
    """Aggregates module should declare native helper surface for sensor aggregates."""
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
    module_entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    assert module_entities == []
    assert len(surfaces) == 1
    assert surfaces[0].unique_id == (
        "magic_areas:entry-1:area-1:aggregates:config_entry_helper:"
        "aggregate_sensor_standard_temperature"
    )
    assert surfaces[0].domain == "group"
    assert surfaces[0].options["group_type"] == SENSOR_DOMAIN
    assert surfaces[0].options["entities"] == ["sensor.temp_1", "sensor.temp_2"]
    assert surfaces[0].options["type"] == "mean"
    assert surfaces[0].area_id == area_config.id


def test_aggregates_module_matches_legacy_binary_entities_and_threshold() -> None:
    """Aggregates module should declare native binary and threshold helper surfaces."""
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
    coordinator = make_coordinator(snapshot)

    module = get_module("aggregates")
    module_entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    assert module_entities == []
    group_surfaces = [surface for surface in surfaces if surface.domain == "group"]
    assert {surface.options["group_type"] for surface in group_surfaces} == {
        BINARY_SENSOR_DOMAIN,
        SENSOR_DOMAIN,
    }
    binary_surface = next(
        surface
        for surface in group_surfaces
        if surface.options["group_type"] == BINARY_SENSOR_DOMAIN
    )
    assert binary_surface.unique_id == (
        "magic_areas:entry-1:area-1:aggregates:config_entry_helper:"
        "aggregate_binary-sensor_standard_motion"
    )
    assert binary_surface.options["entities"] == [
        "binary_sensor.motion_1",
        "binary_sensor.motion_2",
    ]
    assert binary_surface.options["all"] is False

    threshold_surface = next(
        surface for surface in surfaces if surface.domain == "threshold"
    )
    assert threshold_surface.unique_id == (
        "magic_areas:entry-1:area-1:threshold:config_entry_helper:"
        "threshold_light"
    )
    assert threshold_surface.title == "Magic Areas Threshold Kitchen Threshold Light"
    assert threshold_surface.options["entity_id"] == (
        "sensor.magic_areas_aggregates_kitchen_aggregate_illuminance"
    )
    assert threshold_surface.options["upper"] == 50.0
    assert threshold_surface.options["hysteresis"] == 5.0
    assert threshold_surface.options["lower"] is None
    assert threshold_surface.device_class == "light"


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
    assert module.desired_managed_surfaces(area_config, snapshot) == []


def test_aggregates_module_skips_threshold_without_illuminance_aggregate() -> None:
    """Threshold helper should not be declared without a managed source aggregate."""
    area_config = make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                ATTR_ENTITY_ID: "sensor.lux_1",
                ATTR_UNIT_OF_MEASUREMENT: "lx",
            }
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.ILLUMINANCE],
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 50,
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    module = get_module("aggregates")

    assert module.desired_managed_surfaces(area_config, snapshot) == []


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
    assert kwargs["owner_entry_id"] == "entry-1"
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
