"""End-to-end options-flow tests for area options and control groups."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entity_registry import async_get as async_get_er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

from .options_flow_testkit import go_to_step, start_options_flow, submit_step


async def test_options_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Area options flow stores core settings and light-group config."""
    config_entry = init_integration
    er = async_get_er(hass)

    er.async_get_or_create(
        suggested_object_id="test_light",
        unique_id="test_light",
        domain=LIGHT_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    result = await go_to_step(hass, result, "area_config")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {CONF_TYPE: AreaType.EXTERIOR})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "presence_tracking")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(
        hass,
        result,
        {
            CONF_CLEAR_TIMEOUT: 2,
            CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"],
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "secondary_states")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {CONF_SLEEP_TIMEOUT: 3})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "select_features")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {MagicAreasFeatures.LIGHT_GROUPS: True})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "feature_conf_light_groups")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {"overhead_lights": ["light.test_light"]})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_TYPE] == AreaType.EXTERIOR
    assert config_entry.options[CONF_CLEAR_TIMEOUT] == 2
    assert config_entry.options[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]
    assert config_entry.options["secondary_states"][CONF_SLEEP_TIMEOUT] == 3
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ] == {
        "brightness_mode": "inhibit",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: "ignore",
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


async def test_options_flow_custom_control_groups_step(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups should validate and persist through options flow."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    result = await submit_step(
        hass,
        result,
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.task",
                    "members": ["light.test_light"],
                    "trigger_states": ["occupied"],
                    "policy_id": "custom_control_group",
                    "metadata": {"label": "Task"},
                }
            ]
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        config_entry.options[CONF_CUSTOM_CONTROL_GROUPS][0]["group_id"]
        == "control.task"
    )


async def test_options_flow_custom_control_groups_applies_templates_by_default(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups step should seed starter templates when unset."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    result = await submit_step(hass, result, {})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY

    group_ids = {
        group["group_id"] for group in config_entry.options[CONF_CUSTOM_CONTROL_GROUPS]
    }
    assert group_ids == {"control.task", "control.reading", "control.media"}


async def test_options_flow_custom_control_groups_rejects_invalid_payload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups step should reject invalid payloads."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")

    result = await submit_step(
        hass,
        result,
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "members": ["light.test_light"],
                    "trigger_states": ["occupied"],
                }
            ]
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom_control_groups"
    assert result["errors"]


async def test_options_flow_with_light_binary_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary-state dark entity selector accepts light-class binary sensors."""
    config_entry = init_integration
    er = async_get_er(hass)

    er.async_get_or_create(
        suggested_object_id="test_light_sensor",
        unique_id="test_light_sensor",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
        original_device_class=BinarySensorDeviceClass.LIGHT,
    )
    hass.states.async_set(
        "binary_sensor.test_light_sensor",
        "off",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    result = await submit_step(
        hass,
        result,
        {"dark_entity": "binary_sensor.test_light_sensor"},
    )

    assert result["type"] == FlowResultType.MENU
