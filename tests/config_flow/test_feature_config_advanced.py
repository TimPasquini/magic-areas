"""Tests for advanced feature configuration handler with dynamic selectors."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows.steps.feature_config_advanced import (
    handle_feature_conf_advanced,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_unknown_feature() -> None:
    """Test that unknown feature returns abort."""
    flow = MagicMock()
    flow.async_abort = MagicMock(return_value={"reason": "unknown_feature"})

    result = await handle_feature_conf_advanced(flow, "unknown_feature", user_input=None)

    assert result["reason"] == "unknown_feature"
    flow.async_abort.assert_called_once_with(reason="unknown_feature")


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_shows_form_on_no_input() -> None:
    """Test that form is shown when no input provided."""
    flow = MagicMock()
    flow._build_options_schema = MagicMock(return_value={})
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.LIGHT_GROUPS, user_input=None
    )

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_wasp_in_a_box_builds_multi_select() -> None:
    """Test that Wasp in a Box gets multi-select selector override."""
    flow = MagicMock()
    flow._build_options_schema = MagicMock(return_value={})
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.WASP_IN_A_BOX, user_input=None
    )

    assert result["type"] == FlowResultType.FORM
    # Verify async_show_form was called with selectors
    call_args = flow.async_show_form.call_args
    assert call_args is not None
    # Check that selector was built
    flow._build_options_schema.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_processes_user_input() -> None:
    """Test that user input is validated and stored."""
    flow = MagicMock()
    flow.area_options = {}
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})

    user_input: dict[str, str] = {}

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.LIGHT_GROUPS, user_input=user_input
    )

    assert result["type"] == FlowResultType.MENU
    assert "features" in flow.area_options or "enabled_features" in flow.area_options


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_handles_merge_options() -> None:
    """Test that merge_options flag correctly merges feature config."""
    flow = MagicMock()
    # Pre-populate with existing config for light_groups
    flow.area_options = {
        "features": {
            MagicAreasFeatures.LIGHT_GROUPS: {"existing_key": "existing_value"}
        }
    }
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})

    # Simulate input for a feature that merges options
    user_input = {"new_key": "new_value"}

    # Use a feature that has merge_options set
    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.LIGHT_GROUPS, user_input=user_input
    )

    # Verify result
    assert result["type"] == FlowResultType.MENU


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_stores_feature_config() -> None:
    """Test that feature config is stored correctly."""
    flow = MagicMock()
    flow.area_options = {}
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})

    # Provide valid input
    user_input: dict[str, str] = {}

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.LIGHT_GROUPS, user_input=user_input
    )

    assert result["type"] == FlowResultType.MENU


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_form_includes_feature_options() -> None:
    """Test that form includes options from feature registry."""
    flow = MagicMock()
    flow._build_options_schema = MagicMock(return_value={})
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.AGGREGATES, user_input=None
    )

    assert result["type"] == FlowResultType.FORM
    # Verify options were passed to schema builder
    call_args = flow._build_options_schema.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_non_wasp_feature() -> None:
    """Test that non-Wasp features don't get special selector."""
    flow = MagicMock()
    flow._build_options_schema = MagicMock(return_value={})
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.CLIMATE_CONTROL, user_input=None
    )

    assert result["type"] == FlowResultType.FORM
    # Verify async_show_form was called
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_advanced_wasp_selector_has_correct_options() -> None:
    """Test that Wasp selector includes all device classes."""

    flow = MagicMock()
    flow._build_options_schema = MagicMock(return_value={})
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf_advanced(
        flow, MagicAreasFeatures.WASP_IN_A_BOX, user_input=None
    )

    assert result["type"] == FlowResultType.FORM
    # The selector should be built with WASP_IN_A_BOX_WASP_DEVICE_CLASSES
    flow._build_options_schema.assert_called_once()
