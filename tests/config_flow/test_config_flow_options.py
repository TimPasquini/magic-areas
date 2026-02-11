"""Test Magic Areas options flow functionality.

This module contains tests for the options flow menu navigation and core option
handling, excluding feature-specific configuration and error handling.
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
        "custom_components.magic_areas.config_flows.options_flow.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
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
        "custom_components.magic_areas.config_flows.options_flow.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"type": "interior"},
        )

    # Should stay on form
    assert result["type"] == FlowResultType.FORM


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
        "custom_components.magic_areas.config_flows.options_flow.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
        side_effect=vol.MultipleInvalid(
            [vol.Invalid("Error", path=[CONF_CLEAR_TIMEOUT])]
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_CLEAR_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_CLEAR_TIMEOUT: "Error"}

    # Generic Exception
    with patch(
        "custom_components.magic_areas.config_flows.options_flow.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
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
        "custom_components.magic_areas.config_flows.options_flow.SECONDARY_STATES_SCHEMA",
        side_effect=vol.MultipleInvalid(
            [vol.Invalid("Error", path=[CONF_SLEEP_TIMEOUT])]
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SLEEP_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_SLEEP_TIMEOUT: "Error"}

    # Generic Exception
    with patch(
        "custom_components.magic_areas.config_flows.options_flow.SECONDARY_STATES_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SLEEP_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_unknown_step(hass: HomeAssistant, init_integration) -> None:
    """Test options flow with an unknown step."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    with pytest.raises(ValueError, match="Unknown step unknown_step"):
        await flow.async_step("unknown_step")


async def test_options_flow_unknown_feature(
    hass: HomeAssistant, init_integration
) -> None:
    """Test options flow with an unknown feature."""
    config_entry = init_integration

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.context = {"step_id": "feature_conf_non_existent_feature"}
    result = await flow.async_step_feature_conf()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown_feature"


async def test_options_flow_select_features_initializes_enabled_features(
    hass: HomeAssistant, init_integration
) -> None:
    """Test enabling features when the enabled dict is missing."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    coordinator = config_entry.runtime_data.coordinator
    flow.area = coordinator.data.area
    flow.area_options = {}

    result = await flow.async_step_select_features(
        user_input={CONF_FEATURE_LIGHT_GROUPS: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert CONF_ENABLED_FEATURES in flow.area_options


async def test_options_flow_init_skips_missing_light_tracking_state(
    hass: HomeAssistant, init_integration
) -> None:
    """Test missing state entries are ignored for light tracking entities."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    missing_entity = "binary_sensor.missing_light"
    hass.states.async_set(
        missing_entity, "off", {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT}
    )

    original_get = StateMachine.get

    def _patched_get(self: StateMachine, entity_id: str) -> Any:
        if entity_id == missing_entity:
            return None
        return original_get(self, entity_id)

    with patch.object(StateMachine, "get", autospec=True, side_effect=_patched_get):
        await flow.async_step_init()

    assert missing_entity not in flow.all_light_tracking_entities


async def test_options_flow_async_step_routes_feature_conf(
    hass: HomeAssistant, init_integration
) -> None:
    """Test async_step routes feature_conf steps."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()
    flow.context = {}

    result = await flow.async_step("feature_conf_light_groups")

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups"


async def test_options_flow_async_step_feature_conf_unknown_feature(
    hass: HomeAssistant, init_integration
) -> None:
    """Test _async_step_feature_conf with unknown feature key."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {CONF_ENABLED_FEATURES: {}}

    result = await flow._async_step_feature_conf("unknown_feature")

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown_feature"


async def test_options_flow_light_tracking_entities(
    hass: HomeAssistant, init_integration
) -> None:
    """Test that additional light tracking entities are included."""
    config_entry = init_integration

    # The sun.sun entity is created by default by Home Assistant's core config
    await setup.async_setup_component(hass, "sun", {})
    await hass.async_block_till_done()

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    assert "sun.sun" in ADDITIONAL_LIGHT_TRACKING_ENTITIES
    assert "sun.sun" in flow.all_light_tracking_entities


async def test_options_flow_get_feature_list(hass: HomeAssistant) -> None:
    """Test the _get_feature_list method."""
    mock_config_entry = MockConfigEntry(domain=DOMAIN, data={})

    # Regular area - mock coordinator with area data
    flow_regular = OptionsFlowHandler(mock_config_entry)
    mock_coordinator_regular = MagicMock()
    mock_area_regular = MagicMock(spec=MagicArea)
    mock_area_regular.config = {CONF_TYPE: "interior"}
    mock_area_regular.id = "kitchen"
    mock_coordinator_regular.data = MagicMock()
    mock_coordinator_regular.data.area = mock_area_regular
    flow_regular._config_entry.runtime_data = MagicMock()
    flow_regular._config_entry.runtime_data.coordinator = mock_coordinator_regular
    flow_regular.area = mock_coordinator_regular.data.area
    assert flow_regular._get_feature_list() == CONF_FEATURE_LIST

    # Meta area - mock coordinator with area data
    flow_meta = OptionsFlowHandler(mock_config_entry)
    mock_coordinator_meta = MagicMock()
    mock_area_meta = MagicMock(spec=MagicMetaArea)
    mock_area_meta.config = {CONF_TYPE: AREA_TYPE_META}
    mock_area_meta.id = "interior"
    mock_coordinator_meta.data = MagicMock()
    mock_coordinator_meta.data.area = mock_area_meta
    flow_meta._config_entry.runtime_data = MagicMock()
    flow_meta._config_entry.runtime_data.coordinator = mock_coordinator_meta
    flow_meta.area = mock_coordinator_meta.data.area
    assert flow_meta._get_feature_list() == CONF_FEATURE_LIST_META

    # Global meta area - mock coordinator with area data
    flow_global = OptionsFlowHandler(mock_config_entry)
    mock_coordinator_global = MagicMock()
    mock_area_global = MagicMock(spec=MagicMetaArea)
    mock_area_global.config = {CONF_TYPE: AREA_TYPE_META}
    mock_area_global.id = META_AREA_GLOBAL.lower()
    mock_coordinator_global.data = MagicMock()
    mock_coordinator_global.data.area = mock_area_global
    flow_global._config_entry.runtime_data = MagicMock()
    flow_global._config_entry.runtime_data.coordinator = mock_coordinator_global
    flow_global.area = mock_coordinator_global.data.area
    assert flow_global._get_feature_list() == CONF_FEATURE_LIST_GLOBAL


async def test_options_flow_get_configurable_features(hass: HomeAssistant) -> None:
    """Test the _get_configurable_features method."""
    # Mock a config entry, it's needed by the handler's init
    mock_config_entry = MockConfigEntry(domain=DOMAIN, data={})

    # Test with a regular area - mock coordinator with area data
    flow_regular = OptionsFlowHandler(mock_config_entry)
    mock_coordinator_regular = MagicMock()
    mock_area_regular = MagicMock(spec=MagicArea)
    mock_area_regular.is_meta.return_value = False
    mock_coordinator_regular.data = MagicMock()
    mock_coordinator_regular.data.area = mock_area_regular
    flow_regular._config_entry.runtime_data = MagicMock()
    flow_regular._config_entry.runtime_data.coordinator = mock_coordinator_regular
    flow_regular.area = mock_coordinator_regular.data.area
    configurable_regular = flow_regular._get_configurable_features()

    assert CONF_FEATURE_LIGHT_GROUPS in configurable_regular
    assert CONF_FEATURE_FAN_GROUPS in configurable_regular

    # Test with a meta area - mock coordinator with area data
    flow_meta = OptionsFlowHandler(mock_config_entry)
    mock_coordinator_meta = MagicMock()
    mock_area_meta = MagicMock(spec=MagicMetaArea)
    mock_area_meta.is_meta.return_value = True
    mock_coordinator_meta.data = MagicMock()
    mock_coordinator_meta.data.area = mock_area_meta
    flow_meta._config_entry.runtime_data = MagicMock()
    flow_meta._config_entry.runtime_data.coordinator = mock_coordinator_meta
    flow_meta.area = mock_coordinator_meta.data.area
    configurable_meta = flow_meta._get_configurable_features()

    assert CONF_FEATURE_LIGHT_GROUPS not in configurable_meta
    assert CONF_FEATURE_FAN_GROUPS not in configurable_meta
