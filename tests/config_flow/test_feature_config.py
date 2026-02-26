"""Tests for feature configuration step handler."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows.steps.feature_config import (
    handle_feature_conf,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@pytest.mark.asyncio
async def test_handle_feature_conf_unknown_feature() -> None:
    """Test that unknown feature returns abort."""
    flow = MagicMock()
    flow._feature_step_id = "feature_conf_unknown"
    flow.context = {}
    flow.async_abort = MagicMock(return_value={"reason": "unknown_feature"})

    result = await handle_feature_conf(flow, user_input=None)

    assert result["reason"] == "unknown_feature"
    flow.async_abort.assert_called_once_with(reason="unknown_feature")


@pytest.mark.asyncio
async def test_handle_feature_conf_shows_form_on_no_input() -> None:
    """Test that feature config shows form when no input provided."""
    flow = MagicMock()
    flow._feature_step_id = f"feature_conf_{MagicAreasFeatures.LIGHT_GROUPS}"
    flow.context = {}
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
    flow._build_schema_from_vol = MagicMock(return_value={})

    result = await handle_feature_conf(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_with_known_feature() -> None:
    """Test that known feature from registry is handled correctly."""
    flow = MagicMock()
    flow._feature_step_id = f"feature_conf_{MagicAreasFeatures.LIGHT_GROUPS}"
    flow.context = {}
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
    flow._build_schema_from_vol = MagicMock(return_value={})

    result = await handle_feature_conf(flow, user_input=None)

    # Should show form for a known feature
    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_validates_input() -> None:
    """Test that user input is validated using feature schema."""
    flow = MagicMock()
    flow._feature_step_id = f"feature_conf_{MagicAreasFeatures.LIGHT_GROUPS}"
    flow.context = {}
    flow.area_options = {}
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})

    # Provide valid user input
    user_input: dict[str, str] = {}

    result = await handle_feature_conf(flow, user_input=user_input)

    # Should proceed to show_menu on valid input
    assert result["type"] == FlowResultType.MENU


@pytest.mark.asyncio
async def test_handle_feature_conf_stores_valid_feature_config() -> None:
    """Test that valid feature configuration is stored in area_options."""
    flow = MagicMock()
    flow._feature_step_id = f"feature_conf_{MagicAreasFeatures.LIGHT_GROUPS}"
    flow.context = {}
    flow.area_options = {}
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})

    # Provide valid user input
    user_input: dict[str, str] = {}

    result = await handle_feature_conf(flow, user_input=user_input)

    # Should proceed to show_menu
    assert result["type"] == FlowResultType.MENU
    # Check that features dict was created
    assert "features" in flow.area_options
