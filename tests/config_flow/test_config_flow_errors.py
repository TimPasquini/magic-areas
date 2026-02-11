"""Test Magic Areas error handling in config flow.

This module contains tests for error handling in feature configuration,
validation errors, and config base utilities.
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
        "custom_components.magic_areas.config_flows.options_flow.CONFIGURABLE_FEATURES",
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
        "custom_components.magic_areas.config_flows.options_flow.CONFIGURABLE_FEATURES",
        {CONF_FEATURE_LIGHT_GROUPS: MagicMock(side_effect=Exception("Boom"))},
    ):
        result = await flow.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS, options=[], user_input={"some": "input"}
        )

    # Should return form (stay on step)
    assert result["type"] == FlowResultType.FORM


async def test_options_flow_feature_conf_invalid_input(
    hass: HomeAssistant, init_integration
) -> None:
    """Test feature config error handling for invalid input."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    feature_key = "test_feature"
    patched_feature = FeatureConfig(
        name=feature_key,
        options=[("value", 1, int)],
        schema=vol.Schema({vol.Required("value"): int}),
    )
    with patch.dict(FEATURE_REGISTRY, {feature_key: patched_feature}):
        flow.context = {"step_id": f"feature_conf_{feature_key}"}
        result = await flow.async_step_feature_conf(user_input={"value": "bad"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_input"}


async def test_options_flow_do_feature_config_no_schema_value_error(
    hass: HomeAssistant, init_integration
) -> None:
    """Test ValueError when a feature schema is missing."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area = config_entry.runtime_data.area
    flow.area_options = {CONF_ENABLED_FEATURES: {}}

    with patch.dict(CONFIGURABLE_FEATURES, {CONF_FEATURE_LIGHT_GROUPS: None}):
        result = await flow.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS,
            options=[("test", 1, int)],
            user_input={"test": 1},
        )

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_climate_select_presets_no_entity(
    hass: HomeAssistant, init_integration
) -> None:
    """Test climate preset step aborts when no entity is selected."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {CONF_ENABLED_FEATURES: {CONF_FEATURE_CLIMATE_CONTROL: {}}}

    result = await flow.async_step_feature_conf_climate_control_select_presets()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_entity_selected"


async def test_options_flow_climate_select_presets_invalid_entity(
    hass: HomeAssistant, init_integration
) -> None:
    """Test climate preset step aborts for invalid entity."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            CONF_FEATURE_CLIMATE_CONTROL: {
                CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.invalid_entity"
            }
        }
    }

    result = await flow.async_step_feature_conf_climate_control_select_presets()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "invalid_entity"


def test_nullable_entity_selector():
    """Test NullableEntitySelector."""
    selector = NullableEntitySelector(EntitySelectorConfig())

    assert selector(None) is None
    assert selector("") == ""

    # Mock the super call to check it's called for other values
    with patch.object(
        EntitySelector, "__call__", return_value="valid_entity"
    ) as mock_super:
        assert selector("some_entity") == "valid_entity"
        mock_super.assert_called_once_with("some_entity")


def test_config_base_build_schema_no_saved_options():
    """Test _build_options_schema with no saved options."""
    base = ConfigBase()
    # Set config_entry to None to hit the branch
    base.config_entry = None

    options = [("test_option", "default_value", str)]
    schema = base._build_options_schema(options=options)

    # The main thing is that it doesn't crash.
    # We can check the default value logic by seeing what the schema does with empty input.
    assert schema({}) == {"test_option": "default_value"}


def test_config_base_build_selector_select_defaults() -> None:
    """Test selector builder default handling."""
    from custom_components.magic_areas.schemas.selectors import (
        build_selector_select,
    )

    selector = build_selector_select()
    assert selector.config["options"] == []


def test_config_base_build_schema_uses_config_entry_options() -> None:
    """Test _build_options_schema pulls defaults from config entry options."""
    base = ConfigBase()
    base.config_entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={"test_option": "saved_value"}
    )

    options = [("test_option", "default_value", str)]
    schema = base._build_options_schema(options=options)

    option_key = next(iter(schema.schema))
    assert option_key.description["suggested_value"] == "saved_value"
