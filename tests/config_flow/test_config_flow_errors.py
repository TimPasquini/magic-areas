"""Test Magic Areas error handling in config flow.

This module contains tests for error handling in feature configuration,
validation errors, and config base utilities.
"""

from typing import Any, cast
from unittest.mock import patch


import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


async def test_options_flow_feature_conf_invalid_input(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test feature config error handling for invalid input."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    feature_key = MagicAreasFeatures.HEALTH
    patched_feature = FeatureConfig(
        name=feature_key,
        schema=vol.Schema({vol.Required("value"): int}),
    )
    with patch.dict(FEATURE_REGISTRY, {feature_key: patched_feature}):
        flow.context = cast(Any, {"step_id": f"feature_conf_{feature_key.value}"})
        result = await flow.async_step_feature_conf(user_input={"value": "bad"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_input"}




async def test_options_flow_climate_select_presets_no_entity(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test climate preset step aborts when no entity is selected."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {CONF_ENABLED_FEATURES: {MagicAreasFeatures.CLIMATE_CONTROL: {}}}

    result = await flow.async_step_feature_conf_climate_control_select_presets()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_entity_selected"


async def test_options_flow_climate_select_presets_invalid_entity(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test climate preset step aborts for invalid entity."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.CLIMATE_CONTROL: {
                CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.invalid_entity"
            }
        }
    }

    result = await flow.async_step_feature_conf_climate_control_select_presets()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "invalid_entity"


def test_nullable_entity_selector() -> None:
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


def test_config_base_build_schema_no_saved_options() -> None:
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
