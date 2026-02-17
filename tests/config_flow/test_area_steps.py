"""Tests for area configuration step handlers."""

from unittest.mock import MagicMock
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows.steps.area_steps import (
    handle_area_config,
    handle_presence_tracking,
    handle_secondary_states,
)


@pytest.mark.asyncio
async def test_handle_area_config_shows_form_on_no_input() -> None:
    """Test that area config shows form when no input provided."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.name = "kitchen"
    flow.area_options = {}
    flow.all_entities = ["light.kitchen"]
    flow.all_area_entities = ["light.kitchen"]
    flow._build_options_schema = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_area_config(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_presence_tracking_shows_form_on_no_input() -> None:
    """Test that presence tracking shows form when no input provided."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.name = "kitchen"
    flow.area_options = {}
    flow._coordinator_data = MagicMock()
    flow._coordinator_data.presence_sensors = ["binary_sensor.motion"]
    flow._build_options_schema = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_presence_tracking(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_secondary_states_shows_form_on_no_input() -> None:
    """Test that secondary states shows form when no input provided."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.name = "kitchen"
    flow.area_options = {}
    flow.all_light_tracking_entities = ["light.kitchen"]
    flow.all_binary_entities = ["binary_sensor.motion"]
    flow._build_options_schema = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_secondary_states(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_area_config_meta_area() -> None:
    """Test that area config handles meta areas correctly."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = True
    flow._area_config.name = "interior"
    flow.area_options = {}
    flow.all_entities = ["light.kitchen", "light.living_room"]
    flow.all_area_entities = ["light.kitchen", "light.living_room"]
    flow._build_options_schema = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_area_config(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    # Verify it was called with meta area options
    call_args = flow._build_options_schema.call_args
    assert call_args is not None
