"""Test the Magic Areas config flow."""

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol

from homeassistant import config_entries, setup
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from custom_components.magic_areas.config_flow import OptionsFlowHandler

from custom_components.magic_areas.const import (
    AREA_STATE_EXTENDED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_META,
    AREA_TYPE_META,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_ACCENT_ENTITY,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_WASP_IN_A_BOX,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_ID,
    CONF_NAME,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
    DOMAIN,
    META_AREA_GLOBAL,
)
from tests.const import MockAreaIds

MOCK_AREA_ID = MockAreaIds.KITCHEN.value
MOCK_AREA_NAME = "Kitchen"


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    area_registry.async_create(MOCK_AREA_NAME)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: MOCK_AREA_NAME,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_AREA_NAME
    assert result2["data"] == {
        "id": MOCK_AREA_ID,
        "name": MOCK_AREA_NAME,
        "type": "interior",
        "features": {},
        "secondary_states": {
            CONF_ACCENT_ENTITY: "",
            CONF_DARK_ENTITY: "",
            CONF_EXTENDED_TIME: DEFAULT_EXTENDED_TIME,
            CONF_EXTENDED_TIMEOUT: DEFAULT_EXTENDED_TIMEOUT,
            CONF_SLEEP_ENTITY: "",
            CONF_SLEEP_TIMEOUT: DEFAULT_SLEEP_TIMEOUT,
        },
        "include_entities": [],
        "exclude_entities": [],
        "presence_device_platforms": ["media_player", "binary_sensor"],
        "presence_sensor_device_class": ["motion", "occupancy", "presence"],
        "clear_timeout": 1,
        "reload_on_registry_change": True,
        "ignore_diagnostic_entities": True,
        "keep_only_entities": [],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_no_areas(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "config", {})

    # Create config entries for all meta areas to ensure they are filtered out
    for area_id in ["global", "interior", "exterior"]:
        MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ID: area_id, CONF_NAME: area_id.title(), CONF_TYPE: AREA_TYPE_META},
            unique_id=area_id,
            state=ConfigEntryState.LOADED,
        ).add_to_hass(hass)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_more_areas"


async def test_area_already_configured(hass: HomeAssistant) -> None:
    """Test that an already-configured area is not an option."""
    await setup.async_setup_component(hass, "config", {})
    
    # Setup Kitchen
    area_registry = async_get_ar(hass)
    area_registry.async_create(MOCK_AREA_NAME)
    
    # Create config entry for Kitchen
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ID: MOCK_AREA_ID, CONF_NAME: MOCK_AREA_NAME, CONF_TYPE: "interior"},
        unique_id=MOCK_AREA_ID,
        state=ConfigEntryState.LOADED,
    ).add_to_hass(hass)

    # Create config entries for all meta areas to ensure they are filtered out
    for area_id in ["global", "interior", "exterior"]:
        MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ID: area_id, CONF_NAME: area_id.title(), CONF_TYPE: AREA_TYPE_META},
            unique_id=area_id,
            state=ConfigEntryState.LOADED,
        ).add_to_hass(hass)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_more_areas"


async def test_invalid_area(hass: HomeAssistant) -> None:
    """Test we get the form and submit an invalid area."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    area_entry = area_registry.async_create(MOCK_AREA_NAME)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Delete area so it's invalid when configuring
    area_registry.async_delete(area_entry.id)
    await hass.async_block_till_done()

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: MOCK_AREA_NAME,
        },
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "invalid_area"


async def test_options_flow(hass: HomeAssistant, init_integration) -> None:
    """Test options flow."""
    config_entry = init_integration
    er = async_get_er(hass)

    # Create a mock light entity
    er.async_get_or_create(
        suggested_object_id="test_light",
        unique_id="test_light",
        domain=LIGHT_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Area config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "area_config"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "area_config"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_TYPE: AREA_TYPE_EXTERIOR},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Presence tracking
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "presence_tracking"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence_tracking"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLEAR_TIMEOUT: 2,
            CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"],
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Secondary states
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "secondary_states"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "secondary_states"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SLEEP_TIMEOUT: 3},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Feature selection
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_features"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_LIGHT_GROUPS: True},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Light group config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_light_groups"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"overhead_lights": ["light.test_light"]},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    # Finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_TYPE] == AREA_TYPE_EXTERIOR
    assert config_entry.options[CONF_CLEAR_TIMEOUT] == 2
    assert config_entry.options[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]
    assert config_entry.options["secondary_states"][CONF_SLEEP_TIMEOUT] == 3
    assert config_entry.options[CONF_ENABLED_FEATURES][CONF_FEATURE_LIGHT_GROUPS] == {
        "overhead_lights": ["light.test_light"],
        "overhead_lights_states": ["occupied"],
        "overhead_lights_act_on": ["occupancy", "state"],
        "sleep_lights": [],
        "sleep_lights_states": [],
        "sleep_lights_act_on": ["occupancy", "state"],
        "accent_lights": [],
        "accent_lights_states": [],
        "accent_lights_act_on": ["occupancy", "state"],
        "task_lights": [],
        "task_lights_states": [],
        "task_lights_act_on": ["occupancy", "state"],
    }


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
    assert config_entry.options[CONF_ENABLED_FEATURES][
        CONF_FEATURE_PRESENCE_HOLD
    ] == {"presence_hold_timeout": 10}


async def test_options_flow_ble_trackers(
    hass: HomeAssistant, init_integration
) -> None:
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
    assert config_entry.options[CONF_ENABLED_FEATURES][
        CONF_FEATURE_BLE_TRACKERS
    ] == {"ble_tracker_entities": ["sensor.test_sensor"]}


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
    assert config_entry.options[CONF_ENABLED_FEATURES][
        CONF_FEATURE_WASP_IN_A_BOX
    ] == {
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


async def test_form_meta_area(hass: HomeAssistant) -> None:
    """Test we get the form and create a meta area."""
    await setup.async_setup_component(hass, "config", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: f"(Meta) {META_AREA_GLOBAL}",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == META_AREA_GLOBAL
    assert result2["data"][CONF_TYPE] == AREA_TYPE_META
    assert len(mock_setup_entry.mock_calls) == 1


def test_resolve_groups() -> None:
    """Test resolve_groups static method."""
    assert OptionsFlowHandler.resolve_groups(["a", ["b", "c"], "d"]) == [
        "a",
        "b",
        "c",
        "d",
    ]
    assert OptionsFlowHandler.resolve_groups(["a", "b", "a"]) == ["a", "b"]


async def test_user_flow_conflicting_meta_area(hass: HomeAssistant) -> None:
    """Test user flow when a meta area name is already taken by a regular area."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    # Create an area named "Global" which conflicts with MetaAreaType.GLOBAL
    area_registry.async_create("Global")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM


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


async def test_options_flow_validation_error(
    hass: HomeAssistant, init_integration
) -> None:
    """Test validation error in options flow."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to area config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "area_config"}
    )

    # Mock validation error
    with patch(
        "custom_components.magic_areas.config_flow.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=["type"])]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"type": "interior"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"type": "Error"}


async def test_options_flow_generic_exception(
    hass: HomeAssistant, init_integration
) -> None:
    """Test generic exception in options flow."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Go to area config
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "area_config"}
    )

    # Mock generic exception
    with patch(
        "custom_components.magic_areas.config_flow.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"type": "interior"},
        )

    # Should stay on form
    assert result["type"] == FlowResultType.FORM


async def test_do_feature_config_validation_error(
    hass: HomeAssistant, init_integration
) -> None:
    """Test validation error in do_feature_config."""
    config_entry = init_integration

    # Initialize options flow
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area = config_entry.runtime_data.area
    flow.area_options = config_entry.options.copy()
    if CONF_ENABLED_FEATURES not in flow.area_options:
        flow.area_options[CONF_ENABLED_FEATURES] = {}

    # Mock CONFIGURABLE_FEATURES to return a schema that fails
    with patch.dict(
        "custom_components.magic_areas.config_flow.CONFIGURABLE_FEATURES",
        {
            CONF_FEATURE_LIGHT_GROUPS: MagicMock(
                side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=["base"])])
            )
        },
    ):
        result = await flow.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS, options=[], user_input={"some": "input"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "malformed_input"}


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


async def test_options_flow_presence_tracking_exceptions(
    hass: HomeAssistant, init_integration
) -> None:
    """Test exceptions in presence tracking step."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "presence_tracking"}
    )

    # Validation Error
    with patch(
        "custom_components.magic_areas.config_flow.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
        side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=[CONF_CLEAR_TIMEOUT])]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_CLEAR_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_CLEAR_TIMEOUT: "Error"}

    # Generic Exception
    with patch(
        "custom_components.magic_areas.config_flow.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_CLEAR_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_secondary_states_exceptions(
    hass: HomeAssistant, init_integration
) -> None:
    """Test exceptions in secondary states step."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "secondary_states"}
    )

    # Validation Error
    with patch(
        "custom_components.magic_areas.config_flow.SECONDARY_STATES_SCHEMA",
        side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=[CONF_SLEEP_TIMEOUT])]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SLEEP_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_SLEEP_TIMEOUT: "Error"}

    # Generic Exception
    with patch(
        "custom_components.magic_areas.config_flow.SECONDARY_STATES_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SLEEP_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_add_feature(
    hass: HomeAssistant, init_integration
) -> None:
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


async def test_do_feature_config_generic_exception(
    hass: HomeAssistant, init_integration
) -> None:
    """Test generic exception in do_feature_config."""
    config_entry = init_integration

    # Initialize options flow
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area = config_entry.runtime_data.area
    flow.area_options = config_entry.options.copy()
    if CONF_ENABLED_FEATURES not in flow.area_options:
        flow.area_options[CONF_ENABLED_FEATURES] = {}

    # Mock CONFIGURABLE_FEATURES to return a schema that raises Exception
    with patch.dict(
        "custom_components.magic_areas.config_flow.CONFIGURABLE_FEATURES",
        {
            CONF_FEATURE_LIGHT_GROUPS: MagicMock(
                side_effect=Exception("Boom")
            )
        },
    ):
        result = await flow.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS, options=[], user_input={"some": "input"}
        )

    # Should return form (stay on step)
    assert result["type"] == FlowResultType.FORM
