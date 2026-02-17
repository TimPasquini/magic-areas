"""Test Magic Areas options flow functionality.

This module contains tests for the options flow menu navigation and core option
handling, excluding feature-specific configuration and error handling.
"""

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

import voluptuous as vol
from homeassistant import setup
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant, StateMachine
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entity_registry import async_get as async_get_er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import (
    AreaType,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.config_flow import (
    OptionsFlowHandler,
)
from custom_components.magic_areas.config_keys import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
)
from custom_components.magic_areas.const import (
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
)
from custom_components.magic_areas.enums import (
    FEATURE_LIST,
    FEATURE_LIST_GLOBAL,
    FEATURE_LIST_META,
    MagicAreasFeatures,
)


async def test_options_flow(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
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
        user_input={CONF_TYPE: AreaType.EXTERIOR},
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
        user_input={MagicAreasFeatures.LIGHT_GROUPS: True},
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
    assert config_entry.options[CONF_TYPE] == AreaType.EXTERIOR
    assert config_entry.options[CONF_CLEAR_TIMEOUT] == 2
    assert config_entry.options[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]
    assert config_entry.options["secondary_states"][CONF_SLEEP_TIMEOUT] == 3
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] == {
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
    hass: HomeAssistant, init_integration: MockConfigEntry
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
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=["type"])]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"type": "interior"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"type": "Error"}


async def test_options_flow_generic_exception(
    hass: HomeAssistant, init_integration: MockConfigEntry
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
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"type": "interior"},
        )

    # Should stay on form
    assert result["type"] == FlowResultType.FORM


async def test_options_flow_presence_tracking_exceptions(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test exceptions in presence tracking step."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "presence_tracking"}
    )

    # Validation Error
    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
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
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_CLEAR_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_secondary_states_exceptions(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test exceptions in secondary states step."""
    config_entry = init_integration

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "secondary_states"}
    )

    # Validation Error
    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.SECONDARY_STATES_SCHEMA",
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
        "custom_components.magic_areas.config_flows.steps.area_steps.SECONDARY_STATES_SCHEMA",
        side_effect=Exception("Boom"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SLEEP_TIMEOUT: 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_unknown_step(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test options flow with an unknown step."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    with pytest.raises(ValueError, match="Unknown step unknown_step"):
        await flow.async_step("unknown_step")


async def test_options_flow_unknown_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test options flow with an unknown feature."""
    config_entry = init_integration

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.context = cast(Any, {"step_id": "feature_conf_non_existent_feature"})
    result = await flow.async_step_feature_conf()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown_feature"


async def test_options_flow_select_features_initializes_enabled_features(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test enabling features when the enabled dict is missing."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    coordinator = config_entry.runtime_data.coordinator
    coordinator_data = coordinator.data
    flow._area_config = coordinator_data.area_config if coordinator_data else None
    flow._coordinator_data = coordinator_data
    flow.area_options = {}

    result = await flow.async_step_select_features(
        user_input={MagicAreasFeatures.LIGHT_GROUPS: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert CONF_ENABLED_FEATURES in flow.area_options


async def test_options_flow_init_skips_missing_light_tracking_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
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
    hass: HomeAssistant, init_integration: MockConfigEntry
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
    hass: HomeAssistant, init_integration: MockConfigEntry
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
    hass: HomeAssistant, init_integration: MockConfigEntry
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
    """Test the get_feature_list function."""
    from custom_components.magic_areas.config_flows.steps.feature_helpers import (
        get_feature_list,
    )

    # Regular area
    mock_area_config_regular = MagicMock()
    mock_area_config_regular.config = {CONF_TYPE: "interior"}
    mock_area_config_regular.id = "kitchen"
    assert get_feature_list(mock_area_config_regular) == FEATURE_LIST

    # Meta area
    mock_area_config_meta = MagicMock()
    mock_area_config_meta.config = {CONF_TYPE: AreaType.META}
    mock_area_config_meta.id = "interior"
    assert get_feature_list(mock_area_config_meta) == FEATURE_LIST_META

    # Global meta area
    mock_area_config_global = MagicMock()
    mock_area_config_global.config = {CONF_TYPE: AreaType.META}
    mock_area_config_global.id = META_AREA_GLOBAL.lower()
    assert get_feature_list(mock_area_config_global) == FEATURE_LIST_GLOBAL


async def test_options_flow_get_configurable_features(hass: HomeAssistant) -> None:
    """Test the get_configurable_features function."""
    from custom_components.magic_areas.config_flows.steps.feature_helpers import (
        get_configurable_features,
    )

    # Test with a regular area
    mock_area_config_regular = MagicMock()
    mock_area_config_regular.is_meta.return_value = False
    configurable_regular = get_configurable_features(mock_area_config_regular)

    assert MagicAreasFeatures.LIGHT_GROUPS in configurable_regular
    assert MagicAreasFeatures.FAN_GROUPS in configurable_regular

    # Test with a meta area
    mock_area_config_meta = MagicMock()
    mock_area_config_meta.is_meta.return_value = True
    configurable_meta = get_configurable_features(mock_area_config_meta)

    assert MagicAreasFeatures.LIGHT_GROUPS not in configurable_meta
    assert MagicAreasFeatures.FAN_GROUPS not in configurable_meta
