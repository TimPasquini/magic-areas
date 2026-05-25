"""Tests for feature selection step handler."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows.steps import (
    handle_feature_selection,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@pytest.mark.asyncio
async def test_handle_feature_selection_shows_form_on_no_input() -> None:
    """Test that feature selection shows form when no input provided."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
    flow._build_options_schema = MagicMock(return_value={})

    result = await handle_feature_selection(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    flow.async_show_form.assert_called_once()
    call_args = flow.async_show_form.call_args
    assert call_args[1]["step_id"] == "select_features"


@pytest.mark.asyncio
async def test_handle_feature_selection_uses_task_oriented_order() -> None:
    """Feature-selection checkboxes should not inherit implementation registry order."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    flow.area_options = {}
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
    flow._build_options_schema = MagicMock(return_value={})

    result = await handle_feature_selection(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    options = flow._build_options_schema.call_args.kwargs["options"]
    option_keys = [option[0] for option in options]
    assert option_keys[:5] == [
        MagicAreasFeatures.LIGHT_GROUPS.value,
        MagicAreasFeatures.FAN_GROUPS.value,
        MagicAreasFeatures.COVER_GROUPS.value,
        MagicAreasFeatures.CLIMATE_CONTROL.value,
        MagicAreasFeatures.MEDIA_PLAYER_GROUPS.value,
    ]


@pytest.mark.asyncio
async def test_handle_feature_selection_enables_selected_features() -> None:
    """Test that selected features are enabled in area options."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    flow.area_options = {}
    flow._persist_options_and_show_menu = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    # Simulate user selecting light_groups and climate_control features
    user_input = {
        str(MagicAreasFeatures.LIGHT_GROUPS): True,
        str(MagicAreasFeatures.CLIMATE_CONTROL): True,
        str(MagicAreasFeatures.AGGREGATES): False,
    }

    result = await handle_feature_selection(flow, user_input=user_input)

    # Should return menu (next step)
    assert result["type"] == FlowResultType.MENU
    flow._persist_options_and_show_menu.assert_awaited_once()

    # Check that enabled features are stored using HA-serializable string keys.
    assert "features" in flow.area_options
    assert MagicAreasFeatures.LIGHT_GROUPS.value in flow.area_options["features"]
    assert MagicAreasFeatures.CLIMATE_CONTROL.value in flow.area_options["features"]
    assert MagicAreasFeatures.AGGREGATES.value not in flow.area_options["features"]


@pytest.mark.asyncio
async def test_handle_feature_selection_removes_deselected_features() -> None:
    """Test that deselected features are removed from area options."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    # Pre-populate with enabled features using enum members as keys
    flow.area_options = {
        "features": {
            MagicAreasFeatures.LIGHT_GROUPS.value: {},
            MagicAreasFeatures.CLIMATE_CONTROL.value: {},
        }
    }
    flow._persist_options_and_show_menu = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    # Simulate user deselecting climate_control
    user_input = {
        str(MagicAreasFeatures.LIGHT_GROUPS): True,
        str(MagicAreasFeatures.CLIMATE_CONTROL): False,
        str(MagicAreasFeatures.AGGREGATES): False,
    }

    result = await handle_feature_selection(flow, user_input=user_input)

    # Should return menu (next step)
    assert result["type"] == FlowResultType.MENU

    # Check that climate_control was removed
    assert MagicAreasFeatures.LIGHT_GROUPS.value in flow.area_options["features"]
    assert MagicAreasFeatures.CLIMATE_CONTROL.value not in flow.area_options["features"]


@pytest.mark.asyncio
async def test_handle_feature_selection_creates_features_dict() -> None:
    """Test that features dict is created if missing."""
    flow = MagicMock()
    flow._area_config = MagicMock()
    flow._area_config.is_meta.return_value = False
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    flow.area_options = {}
    flow._persist_options_and_show_menu = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    user_input = {
        str(MagicAreasFeatures.LIGHT_GROUPS): True,
    }

    result = await handle_feature_selection(flow, user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert "features" in flow.area_options
    assert MagicAreasFeatures.LIGHT_GROUPS.value in flow.area_options["features"]
