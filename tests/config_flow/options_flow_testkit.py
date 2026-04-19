"""Shared helpers for options-flow tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def start_options_flow(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> ConfigFlowResult:
    """Start options flow for a config entry."""
    return await hass.config_entries.options.async_init(config_entry.entry_id)


async def go_to_step(
    hass: HomeAssistant, flow_result: ConfigFlowResult, step_id: str
) -> ConfigFlowResult:
    """Route an existing options flow to a specific step."""
    return await hass.config_entries.options.async_configure(
        flow_result["flow_id"], user_input={"next_step_id": step_id}
    )


async def submit_step(
    hass: HomeAssistant, flow_result: ConfigFlowResult, user_input: dict[str, object]
) -> ConfigFlowResult:
    """Submit user input to current options-flow step."""
    return await hass.config_entries.options.async_configure(
        flow_result["flow_id"], user_input=user_input
    )
