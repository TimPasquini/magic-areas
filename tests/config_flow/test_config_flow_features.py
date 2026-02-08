"""Test Magic Areas feature configuration in options flow.

This module contains tests for feature-specific configuration handling in the
options flow, including climate control, fan groups, and other features.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import voluptuous as vol
from homeassistant import config_entries, setup
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, StateMachine
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.area_registry import AreaRegistry, async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.floor_registry import async_get as async_get_fr
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_constants import (
    AREA_STATE_EXTENDED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_META,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.area_maps import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
)
from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.config_flow import (
    ConfigBase,

    OptionsFlowHandler,
)
from custom_components.magic_areas.schemas.selectors import (
    NullableEntitySelector,
)
from custom_components.magic_areas.config_flows.feature_registry import (
    FeatureConfig,
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_ID,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.const import (
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_WASP_IN_A_BOX,
)
from custom_components.magic_areas.schemas.features import CONFIGURABLE_FEATURES
from tests.const import MockAreaIds


async def test_options_flow_climate_no_presets(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow for climate entity with no presets."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock climate entity without preset support
    climate_entity = er.async_get_or_create(
        suggested_object_id="test_climate_no_presets",
        unique_id="test_climate_no_presets",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={},  # No presets
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable climate control
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_CLIMATE_CONTROL: True},
    )

    # Go to climate control config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_climate_control"}
    )

    # Select the climate entity, which should lead to the preset selection step, which will abort.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "climate_no_preset_support"


async def test_options_flow_climate_with_presets(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow for climate entity with presets."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock climate entity with preset support
    climate_entity = er.async_get_or_create(
        suggested_object_id="test_climate_with_presets",
        unique_id="test_climate_with_presets",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable climate control
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_CLIMATE_CONTROL: True},
    )

    # Go to climate control config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_climate_control"}
    )

    # Select the climate entity
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )

    # Select presets
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: "home",
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: "away",
        },
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        CONF_FEATURE_CLIMATE_CONTROL
    ] == {
        "entity_id": "climate.test_climate_with_presets",
        "preset_clear": "away",
        "preset_occupied": "home",
        "preset_sleep": "",
        "preset_extended": "",
    }


async def test_options_flow_fan_groups(hass: HomeAssistant, init_integration) -> None:
    """Test options flow for fan groups."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable fan groups
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_FAN_GROUPS: True},
    )

    # Go to fan groups config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_fan_groups"}
    )

    # Configure fan groups
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_GROUPS_REQUIRED_STATE: AREA_STATE_EXTENDED,
            CONF_FAN_GROUPS_SETPOINT: 25.0,
        },
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_FAN_GROUPS] == {
        "required_state": "extended",
        "tracked_device_class": "temperature",
        "setpoint": 25.0,
    }


async def test_options_flow_area_aware_media_player(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow for area aware media player."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock media player entity
    media_player_entity = er.async_get_or_create(
        suggested_object_id="test_media_player",
        unique_id="test_media_player",
        domain=MEDIA_PLAYER_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable area aware media player
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: True},
    )

    # Go to area aware media player config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_area_aware_media_player"},
    )

    # Configure area aware media player
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_NOTIFICATION_DEVICES: [media_player_entity.entity_id]},
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
    ] == {
        "notification_devices": ["media_player.test_media_player"],
        "notification_states": ["extended"],
    }


async def test_options_flow_aggregates(hass: HomeAssistant, init_integration) -> None:
    """Test options flow for aggregates."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable aggregates
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_AGGREGATION: True},
    )

    # Go to aggregates config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_aggregates"}
    )

    # Configure aggregates
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AGGREGATES_MIN_ENTITIES: 3,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 100,
        },
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_AGGREGATION] == {
        "aggregates_min_entities": 3,
        "aggregates_illuminance_threshold": 100,
        "aggregates_binary_sensor_device_classes": [
            "connectivity",
            "door",
            "garage_door",
            "gas",
            "heat",
            "light",
            "lock",
            "moisture",
            "motion",
            "moving",
            "occupancy",
            "presence",
            "problem",
            "safety",
            "smoke",
            "sound",
            "tamper",
            "update",
            "vibration",
            "window",
        ],
        "aggregates_sensor_device_classes": [
            "aqi",
            "atmospheric_pressure",
            "carbon_monoxide",
            "carbon_dioxide",
            "current",
            "energy",
            "energy_storage",
            "gas",
            "humidity",
            "illuminance",
            "irradiance",
            "moisture",
            "nitrogen_dioxide",
            "nitrogen_monoxide",
            "nitrous_oxide",
            "ozone",
            "power",
            "pressure",
            "sulphur_dioxide",
            "temperature",
            "volatile_organic_compounds",
            "volatile_organic_compounds_parts",
        ],
        "aggregates_illuminance_threshold_hysteresis": 0,
    }


async def test_options_flow_presence_hold(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow for presence hold."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable presence hold
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_PRESENCE_HOLD: True},
    )

    # Go to presence hold config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_presence_hold"}
    )

    # Configure presence hold
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_PRESENCE_HOLD_TIMEOUT: 10},
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_PRESENCE_HOLD] == {
        "presence_hold_timeout": 10
    }


async def test_options_flow_ble_trackers(hass: HomeAssistant, init_integration) -> None:
    """Test options flow for BLE trackers."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock sensor entity
    sensor_entity = er.async_get_or_create(
        suggested_object_id="test_sensor",
        unique_id="test_sensor",
        domain=SENSOR_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable BLE trackers
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_BLE_TRACKERS: True},
    )

    # Go to BLE trackers config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_ble_trackers"}
    )

    # Configure BLE trackers
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_BLE_TRACKER_ENTITIES: [sensor_entity.entity_id]},
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_BLE_TRACKERS] == {
        "ble_tracker_entities": ["sensor.test_sensor"]
    }


async def test_options_flow_wasp_in_a_box(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow for Wasp in a Box."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable Wasp in a Box
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_WASP_IN_A_BOX: True},
    )

    # Go to Wasp in a Box config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_wasp_in_a_box"}
    )

    # Configure Wasp in a Box
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WASP_IN_A_BOX_DELAY: 60,
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 5,
        },
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_WASP_IN_A_BOX] == {
        "delay": 60,
        "wasp_timeout": 5,
        "wasp_device_classes": ["motion", "occupancy"],
    }


async def test_options_flow_health(hass: HomeAssistant, init_integration) -> None:
    """Test options flow for health."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Enable health
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_HEALTH: True},
    )

    # Go to health config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_health"}
    )

    # Configure health
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem", "smoke"]},
    )

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_HEALTH] == {
        "health_binary_sensor_device_classes": ["problem", "smoke"]
    }


async def test_options_flow_remove_feature(
    hass: HomeAssistant, init_integration
) -> None:
    """Test removing a feature in options flow."""
    config_entry = init_integration

    # Enable a feature first
    new_data = config_entry.options.copy()
    if CONF_ENABLED_FEATURES not in new_data:
        new_data[CONF_ENABLED_FEATURES] = {}
    new_data[CONF_ENABLED_FEATURES][CONF_FEATURE_LIGHT_GROUPS] = {}

    hass.config_entries.async_update_entry(config_entry, options=new_data)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Deselect light groups
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_LIGHT_GROUPS: False},
    )

    # Verify it's removed from options in the flow (we need to finish to save)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert CONF_FEATURE_LIGHT_GROUPS not in config_entry.options[CONF_ENABLED_FEATURES]


async def test_options_flow_add_feature(hass: HomeAssistant, init_integration) -> None:
    """Test adding a feature in options flow."""
    config_entry = init_integration

    # Ensure feature is NOT enabled
    new_options = config_entry.options.copy()
    if CONF_ENABLED_FEATURES in new_options:
        if CONF_FEATURE_LIGHT_GROUPS in new_options[CONF_ENABLED_FEATURES]:
            del new_options[CONF_ENABLED_FEATURES][CONF_FEATURE_LIGHT_GROUPS]

    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    # Select light groups
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_LIGHT_GROUPS: True},
    )

    # Should go to menu (because it has config)
    assert result["type"] == FlowResultType.MENU

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert CONF_FEATURE_LIGHT_GROUPS in config_entry.options[CONF_ENABLED_FEATURES]


async def test_options_flow_with_light_binary_sensor(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow with a binary sensor of device class light."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock binary sensor entity with device class light
    er.async_get_or_create(
        suggested_object_id="test_light_sensor",
        unique_id="test_light_sensor",
        domain=BINARY_SENSOR_DOMAIN,
        platform="test",
        config_entry=config_entry,
        original_device_class=BinarySensorDeviceClass.LIGHT,
    )
    # We need to set state for it to be picked up by all_entities logic which checks states
    hass.states.async_set(
        "binary_sensor.test_light_sensor",
        "off",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to secondary states where dark_entity selector is used
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "secondary_states"}
    )

    # Verify we can select the binary sensor as dark entity
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_DARK_ENTITY: "binary_sensor.test_light_sensor"},
    )

    assert result["type"] == FlowResultType.MENU


async def test_options_flow_feature_conf_updates_options(
    hass: HomeAssistant, init_integration
) -> None:
    """Test feature config saves options and returns to menu."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    flow.context = {"step_id": "feature_conf_health"}
    result = await flow.async_step_feature_conf(
        user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]}
    )

    assert result["type"] == FlowResultType.MENU
    assert CONF_FEATURE_HEALTH in flow.area_options[CONF_ENABLED_FEATURES]


async def test_options_flow_feature_conf_next_step_calls_handler(
    hass: HomeAssistant, init_integration
) -> None:
    """Test feature config honoring a next step handler."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    patched_feature = FeatureConfig(
        name=CONF_FEATURE_HEALTH,
        options=[],
        next_step="async_step_show_menu",
    )
    with patch.dict(FEATURE_REGISTRY, {CONF_FEATURE_HEALTH: patched_feature}):
        flow.context = {"step_id": "feature_conf_health"}
        result = await flow.async_step_feature_conf(
            user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]}
        )

    assert result["type"] == FlowResultType.MENU


async def test_options_flow_feature_conf_merge_options(
    hass: HomeAssistant, init_integration
) -> None:
    """Test feature config merges options when requested."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()
    flow.area_options[CONF_ENABLED_FEATURES] = {
        "test_feature": {"existing": 1}
    }

    feature_key = "test_feature"
    patched_feature = FeatureConfig(
        name=feature_key,
        options=[("value", 1, int)],
        schema=vol.Schema({vol.Required("value"): int}),
        merge_options=True,
    )
    with patch.dict(FEATURE_REGISTRY, {feature_key: patched_feature}):
        flow.context = {"step_id": f"feature_conf_{feature_key}"}
        result = await flow.async_step_feature_conf(user_input={"value": 2})

    assert result["type"] == FlowResultType.MENU
    assert flow.area_options[CONF_ENABLED_FEATURES][feature_key] == {
        "existing": 1,
        "value": 2,
    }


async def test_options_flow_do_feature_config_merge_options_return_to(
    hass: HomeAssistant, init_integration
) -> None:
    """Test merge options handling and return_to in do_feature_config."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area = config_entry.runtime_data.area
    flow.area_options = {CONF_ENABLED_FEATURES: {}}

    async def _return_to() -> config_entries.ConfigFlowResult:
        return flow.async_abort(reason="return_to")

    result = await flow.do_feature_config(
        name=CONF_FEATURE_HEALTH,
        options=[("test", 1, int)],
        custom_schema=vol.Schema({vol.Optional("test", default=1): int}),
        merge_options=True,
        user_input={"test": 2},
        return_to=_return_to,
    )

    assert result["type"] == FlowResultType.ABORT
    assert flow.area_options[CONF_ENABLED_FEATURES][CONF_FEATURE_HEALTH] == {"test": 2}


async def test_options_flow_do_feature_config_replace_options(
    hass: HomeAssistant, init_integration
) -> None:
    """Test replacing options in do_feature_config."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area = config_entry.runtime_data.area
    flow.area_options = {CONF_ENABLED_FEATURES: {}}

    result = await flow.do_feature_config(
        name=CONF_FEATURE_HEALTH,
        options=[("test", 1, int)],
        custom_schema=vol.Schema({vol.Optional("test", default=1): int}),
        user_input={"test": 3},
    )

    assert result["type"] == FlowResultType.MENU
    assert flow.area_options[CONF_ENABLED_FEATURES][CONF_FEATURE_HEALTH] == {"test": 3}


async def test_options_flow_feature_conf_validation_error(
    hass: HomeAssistant, init_integration
) -> None:
    """Test validation error in _async_step_feature_conf."""
    config_entry = init_integration

    # Enable a feature
    options = config_entry.options.copy()
    options.setdefault(CONF_ENABLED_FEATURES, {})[CONF_FEATURE_HEALTH] = {}
    hass.config_entries.async_update_entry(config_entry, options=options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature config step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_health"}
    )

    # Mock schema to raise validation error
    with patch.dict(
        "custom_components.magic_areas.config_flow.CONFIGURABLE_FEATURES",
        {CONF_FEATURE_HEALTH: MagicMock(side_effect=vol.MultipleInvalid("Boom"))},
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_health"
    assert result["errors"] == {"base": "invalid_input"}


async def test_options_flow_wasp_in_a_box_selector(
    hass: HomeAssistant, init_integration
) -> None:
    """Test that Wasp in a Box feature config uses a multi-select selector."""
    config_entry = init_integration

    # Enable feature
    options = config_entry.options.copy()
    options.setdefault(CONF_ENABLED_FEATURES, {})[CONF_FEATURE_WASP_IN_A_BOX] = {}
    hass.config_entries.async_update_entry(config_entry, options=options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to feature config step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_wasp_in_a_box"}
    )

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    wasp_classes_validator = schema[
        vol.Optional(CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES)
    ]
    assert isinstance(wasp_classes_validator, SelectSelector)
    assert wasp_classes_validator.config["multiple"] is True
