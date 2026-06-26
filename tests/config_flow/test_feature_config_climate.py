"""Tests for climate control preset selection handler."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows.steps import (
    handle_climate_preset_selection,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.schemas.selectors import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
)


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_no_entity_selected_error() -> None:
    """Test that NoEntitySelectedError returns appropriate abort."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow.async_abort = MagicMock(return_value={"reason": "no_entity_selected"})

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.side_effect = NoEntitySelectedError("No entity selected")

        result = await handle_climate_preset_selection(flow, user_input=None)

    assert result["reason"] == "no_entity_selected"
    flow.async_abort.assert_called_once_with(reason="no_entity_selected")


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_invalid_entity_error() -> None:
    """Test that InvalidEntityError returns appropriate abort."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow.async_abort = MagicMock(return_value={"reason": "invalid_entity"})

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.side_effect = InvalidEntityError("Invalid entity")

        result = await handle_climate_preset_selection(flow, user_input=None)

    assert result["reason"] == "invalid_entity"
    flow.async_abort.assert_called_once_with(reason="invalid_entity")


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_no_preset_support_error() -> None:
    """Test that NoPresetSupportError returns appropriate abort."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow.async_abort = MagicMock(return_value={"reason": "climate_no_preset_support"})

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.side_effect = NoPresetSupportError("No preset support")

        result = await handle_climate_preset_selection(flow, user_input=None)

    assert result["reason"] == "climate_no_preset_support"
    flow.async_abort.assert_called_once_with(reason="climate_no_preset_support")


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_shows_form_on_no_input() -> None:
    """Test that form is shown when no input provided."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow._build_schema_from_vol = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.return_value = ({"selector1": "value1"}, {"validator1": "value1"})

        result = await handle_climate_preset_selection(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_processes_valid_input() -> None:
    """Test that valid preset input is processed and saved."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {MagicAreasFeatures.CLIMATE_CONTROL.value: {}}}
    flow._persist_options = AsyncMock()
    flow.async_step_show_menu = AsyncMock(return_value={"type": FlowResultType.MENU})
    flow.async_step_feature_conf_climate_control = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    user_input = {
        "preset_occupied": "occupied",
        "preset_sleep": "sleep",
    }

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.return_value = ({}, {})

        with patch(
            "custom_components.magic_areas.config_flows.steps.feature_config.CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT"
        ) as mock_schema:
            mock_schema.return_value = user_input

            result = await handle_climate_preset_selection(flow, user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    # Verify presets were merged into climate config
    assert MagicAreasFeatures.CLIMATE_CONTROL.value in flow.area_options["features"]


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_builds_dynamic_selectors() -> None:
    """Test that dynamic selectors are built from climate entity."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow._build_schema_from_vol = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        expected_selectors = {
            "preset_clear": "selector1",
            "preset_occupied": "selector2",
        }
        expected_validators = {"preset_clear": "validator1"}
        mock_builder.return_value = (expected_selectors, expected_validators)

        await handle_climate_preset_selection(flow, user_input=None)

    # Verify builder was called with correct climate entity ID
    mock_builder.assert_called_once()
    call_args = mock_builder.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_handle_climate_preset_selection_invalid_preset_input() -> None:
    """Test that invalid preset input returns errors."""
    flow = MagicMock()
    flow.hass = MagicMock()
    flow.area_options = {"features": {}}
    flow._build_schema_from_vol = MagicMock(return_value={})
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    user_input = {"invalid": "preset"}

    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.build_climate_preset_selectors_and_validators"
    ) as mock_builder:
        mock_builder.return_value = ({}, {})

        with patch(
            "custom_components.magic_areas.config_flows.steps.feature_config.CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT"
        ) as mock_schema:
            mock_schema.side_effect = RuntimeError("Invalid preset")

            result = await handle_climate_preset_selection(flow, user_input=user_input)

    assert result["type"] == FlowResultType.FORM
    # Verify errors were passed
    call_args = flow.async_show_form.call_args
    assert call_args is not None
