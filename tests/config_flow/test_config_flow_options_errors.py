"""Error-path and edge-case tests for options flow."""

from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_flow import OptionsFlowHandler
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_SLEEP_TIMEOUT,
)

from .options_flow_testkit import go_to_step, start_options_flow, submit_step


async def test_options_flow_validation_error(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Validation errors on area config should return field-level errors."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "area_config")

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=vol.MultipleInvalid([vol.Invalid("Error", path=["type"])]),
    ):
        result = await submit_step(hass, result, {"type": "interior"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"type": "Error"}


async def test_options_flow_runtime_error(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Runtime errors on area config should keep flow on same form."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "area_config")

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
        side_effect=RuntimeError("Boom"),
    ):
        result = await submit_step(hass, result, {"type": "interior"})

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_presence_tracking_exceptions(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence tracking step should expose validation errors and recover on generic errors."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "presence_tracking")

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.handle_step_validation",
        return_value=({CONF_CLEAR_TIMEOUT: "Error"}, False),
    ):
        result = await submit_step(hass, result, {CONF_CLEAR_TIMEOUT: 1})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_CLEAR_TIMEOUT: "Error"}

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.handle_step_validation",
        return_value=({}, False),
    ):
        result = await submit_step(hass, result, {CONF_CLEAR_TIMEOUT: 1})

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_secondary_states_exceptions(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary states step should expose validation errors and recover on generic errors."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.handle_step_validation",
        return_value=({CONF_SLEEP_TIMEOUT: "Error"}, False),
    ):
        result = await submit_step(hass, result, {CONF_SLEEP_TIMEOUT: 1})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_SLEEP_TIMEOUT: "Error"}

    with patch(
        "custom_components.magic_areas.config_flows.steps.area_steps.handle_step_validation",
        return_value=({}, False),
    ):
        result = await submit_step(hass, result, {CONF_SLEEP_TIMEOUT: 1})

    assert result["type"] == FlowResultType.FORM


async def test_options_flow_unknown_step(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Unknown async_step ids should raise ValueError."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    with pytest.raises(ValueError, match="Unknown step unknown_step"):
        await flow.async_step("unknown_step")


async def test_options_flow_unknown_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Unknown feature step ids should abort with unknown_feature."""
    config_entry = init_integration

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow._feature_step_id = "feature_conf_non_existent_feature"
    result = await flow.async_step_feature_conf()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown_feature"


async def test_options_flow_async_step_feature_conf_unknown_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Unknown feature key in cached feature step should abort."""
    config_entry = init_integration
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    flow.area_options = {CONF_ENABLED_FEATURES: {}}
    flow._feature_step_id = "feature_conf_area"

    result = await flow.async_step_feature_conf()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown_feature"


async def test_options_flow_custom_control_groups_step_meta_area(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Meta-area options flow should allow custom control groups."""
    config_entry = next(
        entry
        for entry in init_integration_all_areas
        if entry.data.get("type") == "meta"
    )

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    result = await submit_step(
        hass,
        result,
        {
            "custom_control_groups": [
                {
                    "group_id": "control.meta_task",
                    "members": ["light.test_light"],
                    "trigger_states": ["occupied"],
                    "policy_id": "custom_control_group",
                }
            ]
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        config_entry.options["custom_control_groups"][0]["group_id"]
        == "control.meta_task"
    )
