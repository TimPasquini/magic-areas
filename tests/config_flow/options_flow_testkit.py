"""Shared helpers for options-flow tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from pytest_homeassistant_custom_component.common import MockConfigEntry

_ROOT_SECTION_SETTINGS = {
    "area_config": "area_config_settings",
    "presence_tracking": "presence_tracking_settings",
    "secondary_states": "secondary_states_settings",
    "custom_control_groups": "custom_control_groups_settings",
}


async def start_options_flow(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> ConfigFlowResult:
    """Start options flow for a config entry."""
    return await hass.config_entries.options.async_init(config_entry.entry_id)


async def go_to_step(
    hass: HomeAssistant, flow_result: ConfigFlowResult, step_id: str
) -> ConfigFlowResult:
    """Route an existing options flow to a specific step."""
    menu_options = flow_result.get("menu_options", [])
    if (
        flow_result.get("type") == "menu"
        and isinstance(menu_options, list)
        and step_id not in menu_options
        and "show_menu" in menu_options
    ):
        flow_result = await hass.config_entries.options.async_configure(
            flow_result["flow_id"], user_input={"next_step_id": "show_menu"}
        )

    result = await hass.config_entries.options.async_configure(
        flow_result["flow_id"], user_input={"next_step_id": step_id}
    )
    settings_step = _ROOT_SECTION_SETTINGS.get(step_id)
    if (
        settings_step is not None
        and result.get("type") == "menu"
        and settings_step in result.get("menu_options", [])
    ):
        return await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": settings_step}
        )
    return result


async def submit_step(
    hass: HomeAssistant, flow_result: ConfigFlowResult, user_input: dict[str, object]
) -> ConfigFlowResult:
    """Submit user input to current options-flow step."""
    return await hass.config_entries.options.async_configure(
        flow_result["flow_id"], user_input=user_input
    )
