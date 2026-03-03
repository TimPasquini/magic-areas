"""Contract tests for feature module implementations."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    CONF_BLE_TRACKER_ENTITIES,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.group_registry import GroupRegistry
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.sensor.aggregate_factory import (
    create_aggregate_sensors as create_sensor_aggregates,
)
from custom_components.magic_areas.binary_sensor import (
    create_aggregate_sensors as create_binary_aggregates,
    create_wasp_in_a_box_sensor,
)
from custom_components.magic_areas.binary_sensor.threshold import (
    create_illuminance_threshold,
)
from custom_components.magic_areas.features.base import FeatureModule


def _make_area_config() -> AreaConfig:
    return AreaConfig(
        id="area-1",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=MagicMock(),
    )


def _make_coordinator(snapshot: MagicMock, hass: object | None = None) -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    coordinator.hass = hass if hass is not None else MagicMock()
    return coordinator


def _make_snapshot(*, enabled: set[MagicAreasFeatures], feature_configs: dict, entities: dict) -> MagicMock:
    snapshot = MagicMock()
    snapshot.enabled_features = enabled
    snapshot.feature_configs = feature_configs
    snapshot.entities = entities
    snapshot.magic_entities = {}
    snapshot.entity_references = MagicMock(
        aggregates_by_device_class={},
        binary_aggregates_by_device_class={},
    )
    return snapshot


def _get_aggregates_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.aggregates import (  # type: ignore[import-not-found]
            AggregatesFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover - exercised in red-first phase
        pytest.fail(
            "AggregatesFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.aggregates)"
        )
    return cast(FeatureModule, AggregatesFeatureModule())


def _get_wasp_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.wasp_in_a_box import (  # type: ignore[import-not-found]
            WaspInABoxFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover - exercised in red-first phase
        pytest.fail(
            "WaspInABoxFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.wasp_in_a_box)"
        )
    return cast(FeatureModule, WaspInABoxFeatureModule())


def _get_light_groups_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.light_groups import (  # type: ignore[import-not-found]
            LightGroupsFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover - exercised in red-first phase
        pytest.fail(
            "LightGroupsFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.light_groups)"
        )
    return cast(FeatureModule, LightGroupsFeatureModule())


def _get_fan_groups_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.fan_groups import (  # type: ignore[import-not-found]
            FanGroupsFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "FanGroupsFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.fan_groups)"
        )
    return cast(FeatureModule, FanGroupsFeatureModule())


def _get_media_player_groups_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.media_player_groups import (  # type: ignore[import-not-found]
            MediaPlayerGroupsFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "MediaPlayerGroupsFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.media_player_groups)"
        )
    return cast(FeatureModule, MediaPlayerGroupsFeatureModule())


def _get_cover_groups_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.cover_groups import (  # type: ignore[import-not-found]
            CoverGroupsFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "CoverGroupsFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.cover_groups)"
        )
    return cast(FeatureModule, CoverGroupsFeatureModule())


def _get_presence_hold_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.presence_hold import (  # type: ignore[import-not-found]
            PresenceHoldFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "PresenceHoldFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.presence_hold)"
        )
    return cast(FeatureModule, PresenceHoldFeatureModule())


def _get_climate_control_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.climate_control import (  # type: ignore[import-not-found]
            ClimateControlFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "ClimateControlFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.climate_control)"
        )
    return cast(FeatureModule, ClimateControlFeatureModule())


def _get_health_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.health import (  # type: ignore[import-not-found]
            HealthFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "HealthFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.health)"
        )
    return cast(FeatureModule, HealthFeatureModule())


def _get_ble_tracker_module() -> FeatureModule:
    try:
        from custom_components.magic_areas.features.modules.ble_trackers import (  # type: ignore[import-not-found]
            BLETrackersFeatureModule,
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            "BLETrackersFeatureModule not implemented yet (expected in "
            "custom_components.magic_areas.features.modules.ble_trackers)"
        )
    return cast(FeatureModule, BLETrackersFeatureModule())


def test_aggregates_module_matches_legacy_sensor_entities() -> None:
    """Aggregates module should match legacy sensor aggregate output."""
    area_config = _make_area_config()
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    legacy_entities = create_sensor_aggregates(
        snapshot, entities_by_domain, area_config, coordinator
    )

    module = _get_aggregates_module()
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    legacy_ids = sorted(entity.entity_id for entity in legacy_entities)
    module_ids = sorted(
        entity.entity_id for entity in module_entities if entity.entity_id.startswith("sensor.")
    )

    assert module_ids == legacy_ids


@pytest.mark.asyncio
async def test_aggregates_module_matches_legacy_binary_entities_and_threshold(
    hass: HomeAssistant,
) -> None:
    """Aggregates module should match legacy binary aggregates and threshold output."""
    area_config = _make_area_config()
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE,
                ATTR_ENTITY_ID: "sensor.lux_1",
                ATTR_UNIT_OF_MEASUREMENT: "lx",
            },
        ],
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_DEVICE_CLASS: "motion",
                ATTR_ENTITY_ID: "binary_sensor.motion_1",
            },
            {
                ATTR_DEVICE_CLASS: "motion",
                ATTR_ENTITY_ID: "binary_sensor.motion_2",
            },
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    snapshot.entity_references.aggregates_by_device_class = {
        SensorDeviceClass.ILLUMINANCE: "sensor.magic_areas_aggregates_kitchen_aggregate_illuminance"
    }
    coordinator = _make_coordinator(snapshot, hass)

    legacy_entities = create_binary_aggregates(
        snapshot, entities_by_domain, area_config, coordinator
    )
    threshold_entity = create_illuminance_threshold(
        hass, snapshot, area_config, coordinator
    )
    if threshold_entity:
        legacy_entities.append(threshold_entity)

    module = _get_aggregates_module()
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    legacy_ids = sorted(entity.entity_id for entity in legacy_entities)
    module_ids = sorted(
        entity.entity_id for entity in module_entities if entity.entity_id.startswith("binary_sensor.")
    )

    assert module_ids == legacy_ids


def test_aggregates_module_respects_min_entities_config() -> None:
    """Aggregates module should respect min-entities config like legacy."""
    area_config = _make_area_config()
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    legacy_entities = create_sensor_aggregates(
        snapshot, entities_by_domain, area_config, coordinator
    )

    module = _get_aggregates_module()
    module_entities = module.build_entities(area_config, coordinator, snapshot)

    assert legacy_entities == []
    assert module_entities == []


def test_aggregates_module_registers_group_registry_definitions() -> None:
    """Aggregates module should register canonical aggregate definitions in group registry."""
    area_config = _make_area_config()
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_aggregates_module()

    with patch(
        "custom_components.magic_areas.features.modules.aggregates.register_aggregate_definitions"
    ) as register_defs:
        module.build_entities(area_config, coordinator, snapshot)

    register_defs.assert_called_once()
    _, kwargs = register_defs.call_args
    assert kwargs["area_id"] == area_config.id
    assert any(
        definition.domain == SENSOR_DOMAIN and definition.device_class == SensorDeviceClass.TEMPERATURE
        for definition in kwargs["definitions"]
    )


def test_aggregates_module_registers_health_definition_without_creating_health_aggregate_entity() -> None:
    """Aggregates module should register health definitions but not emit health aggregate entities."""
    area_config = _make_area_config()
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.HEALTH},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_aggregates_module()

    with patch(
        "custom_components.magic_areas.features.modules.aggregates.register_aggregate_definitions"
    ) as register_defs:
        module_entities = module.build_entities(area_config, coordinator, snapshot)

    _, kwargs = register_defs.call_args
    assert any(
        definition.domain == BINARY_SENSOR_DOMAIN
        and definition.device_class == "problem"
        for definition in kwargs["definitions"]
    )
    assert all(
        "_aggregate_problem" not in entity.entity_id
        for entity in module_entities
        if getattr(entity, "entity_id", None)
    )


def test_wasp_module_matches_legacy_entities_and_config() -> None:
    """Wasp module should match legacy output and config usage."""
    area_config = _make_area_config()
    feature_configs = {
        MagicAreasFeatures.WASP_IN_A_BOX: {
            CONF_WASP_IN_A_BOX_DELAY: 3,
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 7,
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES: ["motion"],
        }
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.AGGREGATES, MagicAreasFeatures.WASP_IN_A_BOX},
        feature_configs=feature_configs,
        entities={},
    )
    coordinator = _make_coordinator(snapshot)

    legacy_entities = create_wasp_in_a_box_sensor(snapshot, area_config, coordinator)

    module = _get_wasp_module()
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
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.WASP_IN_A_BOX},
        feature_configs={},
        entities={},
    )
    module = _get_wasp_module()

    assert module.is_enabled(snapshot) is False


def test_aggregates_module_does_not_attach_listeners() -> None:
    """Aggregates module should not attach extra listeners."""
    module = _get_aggregates_module()

    with (
        patch("homeassistant.helpers.dispatcher.async_dispatcher_connect") as dispatcher_connect,
        patch("homeassistant.helpers.event.async_track_state_change_event") as track_state_change,
    ):
        module.attach_listeners([], MagicMock())

    dispatcher_connect.assert_not_called()
    track_state_change.assert_not_called()


def test_wasp_module_does_not_attach_listeners() -> None:
    """Wasp module should not attach extra listeners."""
    module = _get_wasp_module()

    with (
        patch("homeassistant.helpers.dispatcher.async_dispatcher_connect") as dispatcher_connect,
        patch("homeassistant.helpers.event.async_track_state_change_event") as track_state_change,
    ):
        module.attach_listeners([], MagicMock())

    dispatcher_connect.assert_not_called()
    track_state_change.assert_not_called()


def test_light_groups_module_builds_expected_entities() -> None:
    """Light groups module should build overhead + all groups."""
    area_config = _make_area_config()
    entities_by_domain = {
        "light": [
            {"entity_id": "light.overhead_1"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            "overhead_lights": ["light.overhead_1"],
            "overhead_lights_states": ["occupied", "bright"],
            "overhead_lights_act_on": ["occupancy", "state"],
        }
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_light_groups_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == [
        "light.magic_areas_light_groups_kitchen_all_lights",
        "light.magic_areas_light_groups_kitchen_overhead_lights",
        "switch.magic_areas_light_groups_kitchen_light_control",
    ]


def test_light_groups_module_registers_default_control_groups() -> None:
    """Light module should register area-scoped default control-group definitions."""
    area_config = _make_area_config()
    entities_by_domain = {
        "light": [
            {"entity_id": "light.overhead_1"},
            {"entity_id": "light.task_1"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            "overhead_lights": ["light.overhead_1"],
            "overhead_lights_states": ["occupied", "bright"],
            "overhead_lights_act_on": ["occupancy", "state"],
            "task_lights": ["light.task_1"],
            "task_lights_states": ["occupied"],
            "task_lights_act_on": ["occupancy"],
        }
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_light_groups_module()
    registry = GroupRegistry()

    with patch(
        "custom_components.magic_areas.features.modules.light_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, coordinator, snapshot)

    registered = registry.get_for_area(area_config.id)
    registered_ids = sorted(group.definition.group_id for group in registered)
    assert registered_ids == [
        "light_groups_area-1_all_lights",
        "light_groups_area-1_overhead_lights",
        "light_groups_area-1_task_lights",
    ]


def test_light_groups_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Light module should replace prior light_groups policy entries on rebuild."""
    area_config = _make_area_config()
    module = _get_light_groups_module()
    registry = GroupRegistry()

    initial_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
                "task_lights": ["light.task_1"],
                "task_lights_states": ["occupied"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}, {"entity_id": "light.task_1"}]},
    )
    updated_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )

    with patch(
        "custom_components.magic_areas.features.modules.light_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, _make_coordinator(initial_snapshot), initial_snapshot)
        module.build_entities(area_config, _make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {group.definition.group_id for group in registry.get_for_area(area_config.id)}
    assert "light_groups_area-1_overhead_lights" in group_ids
    assert "light_groups_area-1_task_lights" not in group_ids


def test_fan_groups_module_builds_group_and_control_switch() -> None:
    """Fan groups module should build fan group and control switch."""
    area_config = _make_area_config()
    entities_by_domain = {
        FAN_DOMAIN: [
            {"entity_id": "fan.ceiling_1"},
        ]
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={},
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_fan_groups_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == [
        "fan.magic_areas_fan_groups_kitchen_fan_group",
        "switch.magic_areas_fan_groups_kitchen_fan_control",
    ]


def test_fan_groups_module_registers_default_control_group() -> None:
    """Fan module should register area-scoped default control-group definitions."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={FAN_DOMAIN: [{"entity_id": "fan.ceiling_1"}]},
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_fan_groups_module()
    registry = GroupRegistry()

    with patch(
        "custom_components.magic_areas.features.modules.fan_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, coordinator, snapshot)

    groups = registry.get_for_area(area_config.id)
    assert any(
        group.definition.group_id == "fan_groups_area-1_fan_group" for group in groups
    )


def test_fan_groups_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Fan module should clear stale fan_groups entries when no fan entities remain."""
    area_config = _make_area_config()
    module = _get_fan_groups_module()
    registry = GroupRegistry()

    initial_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={FAN_DOMAIN: [{"entity_id": "fan.ceiling_1"}]},
    )
    updated_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={},
    )

    with patch(
        "custom_components.magic_areas.features.modules.fan_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, _make_coordinator(initial_snapshot), initial_snapshot)
        module.build_entities(area_config, _make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {group.definition.group_id for group in registry.get_for_area(area_config.id)}
    assert "fan_groups_area-1_fan_group" not in group_ids


def test_media_player_groups_module_builds_group_and_control_switch() -> None:
    """Media player groups module should build group and control switch."""
    area_config = _make_area_config()
    entities_by_domain = {
        MEDIA_PLAYER_DOMAIN: [
            {"entity_id": "media_player.tv"},
        ]
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_media_player_groups_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == [
        "media_player.magic_areas_media_player_groups_kitchen_media_player_group",
        "switch.magic_areas_media_player_groups_kitchen_media_player_control",
    ]


def test_media_player_groups_module_registers_default_control_group() -> None:
    """Media-player module should register area-scoped default control-group definitions."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={MEDIA_PLAYER_DOMAIN: [{"entity_id": "media_player.tv"}]},
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_media_player_groups_module()
    registry = GroupRegistry()

    with patch(
        "custom_components.magic_areas.features.modules.media_player_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, coordinator, snapshot)

    groups = registry.get_for_area(area_config.id)
    assert any(
        group.definition.group_id == "media_player_groups_area-1_media_player_group"
        for group in groups
    )


def test_media_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Media module should clear stale media_player_groups entries on rebuild."""
    area_config = _make_area_config()
    module = _get_media_player_groups_module()
    registry = GroupRegistry()

    initial_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={MEDIA_PLAYER_DOMAIN: [{"entity_id": "media_player.tv"}]},
    )
    updated_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={},
    )

    with patch(
        "custom_components.magic_areas.features.modules.media_player_groups.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, _make_coordinator(initial_snapshot), initial_snapshot)
        module.build_entities(area_config, _make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {group.definition.group_id for group in registry.get_for_area(area_config.id)}
    assert "media_player_groups_area-1_media_player_group" not in group_ids


def test_cover_groups_module_builds_device_class_groups() -> None:
    """Cover groups module should build groups per device class and none."""
    area_config = _make_area_config()
    entities_by_domain = {
        COVER_DOMAIN: [
            {"entity_id": "cover.blind_1", "device_class": "blind"},
            {"entity_id": "cover.other_1", "device_class": None},
        ]
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.COVER_GROUPS},
        feature_configs={},
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_cover_groups_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == [
        "cover.magic_areas_cover_groups_kitchen_cover_group",
        "cover.magic_areas_cover_groups_kitchen_cover_group_blind",
    ]


def test_presence_hold_module_builds_switch() -> None:
    """Presence hold module should build the presence hold switch."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.PRESENCE_HOLD},
        feature_configs={},
        entities={},
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_presence_hold_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == [
        "switch.magic_areas_presence_hold_kitchen"
    ]


def test_climate_control_module_builds_switch() -> None:
    """Climate control module should build the climate control switch."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {
                CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen",
            }
        },
        entities={},
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_climate_control_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == [
        "switch.magic_areas_climate_control_kitchen"
    ]


def test_climate_control_module_registers_default_control_group() -> None:
    """Climate module should register default control-group definition."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {
                CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen",
            }
        },
        entities={},
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_climate_control_module()
    registry = GroupRegistry()

    with patch(
        "custom_components.magic_areas.features.modules.climate_control.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, coordinator, snapshot)

    groups = registry.get_for_area(area_config.id)
    assert any(
        group.definition.group_id == "climate_control_area-1_climate_control"
        for group in groups
    )


def test_climate_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Climate module should clear stale climate_control entries when unset."""
    area_config = _make_area_config()
    module = _get_climate_control_module()
    registry = GroupRegistry()

    initial_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {
                CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen",
            }
        },
        entities={},
    )
    updated_snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={MagicAreasFeatures.CLIMATE_CONTROL: {}},
        entities={},
    )

    with patch(
        "custom_components.magic_areas.features.modules.climate_control.GROUP_REGISTRY",
        registry,
    ):
        module.build_entities(area_config, _make_coordinator(initial_snapshot), initial_snapshot)
        module.build_entities(area_config, _make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {group.definition.group_id for group in registry.get_for_area(area_config.id)}
    assert "climate_control_area-1_climate_control" not in group_ids


def test_climate_control_module_skips_switch_without_entity() -> None:
    """Climate module should not build switch when climate entity is unset."""
    area_config = _make_area_config()
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={MagicAreasFeatures.CLIMATE_CONTROL: {}},
        entities={},
    )
    coordinator = _make_coordinator(snapshot)
    module = _get_climate_control_module()

    entities = module.build_entities(area_config, coordinator, snapshot)

    assert entities == []


def test_health_module_builds_health_sensor() -> None:
    """Health module should build the health aggregate sensor."""
    area_config = _make_area_config()
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "binary_sensor.smoke_1",
                ATTR_DEVICE_CLASS: BinarySensorDeviceClass.SMOKE.value,
            }
        ]
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.HEALTH},
        feature_configs={},
        entities=entities_by_domain,
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_health_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == [
        "binary_sensor.magic_areas_health_kitchen_health_problem"
    ]


def test_ble_tracker_module_builds_monitor_sensor() -> None:
    """BLE tracker module should build the tracker monitor sensor."""
    area_config = _make_area_config()
    feature_configs = {
        MagicAreasFeatures.BLE_TRACKER: {
            CONF_BLE_TRACKER_ENTITIES: ["sensor.ble_1"],
        }
    }
    snapshot = _make_snapshot(
        enabled={MagicAreasFeatures.BLE_TRACKER},
        feature_configs=feature_configs,
        entities={},
    )
    coordinator = _make_coordinator(snapshot)

    module = _get_ble_tracker_module()
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == [
        "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    ]
