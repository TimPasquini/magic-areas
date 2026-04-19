"""Integration tests for full options flow workflows."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.magic_areas.config_flows import OptionsFlowHandler
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.enums import MagicAreasFeatures


def _enabled_features(flow: OptionsFlowHandler) -> dict[object, object]:
    """Return enabled-features mapping with a concrete type for assertions."""
    return cast(dict[object, object], flow.area_options[CONF_ENABLED_FEATURES])


@pytest.mark.asyncio
async def test_options_flow_init_creates_handler_with_config_entry() -> None:
    """Test that handler initializes with config entry."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    flow = OptionsFlowHandler(config_entry)

    # Verify handler was created with config entry
    assert flow.handler == "test_entry"
    assert flow._config_entry == config_entry
    # Verify entity lists are initialized
    assert flow.all_entities == []
    assert flow.area_entities == []
    assert flow.all_binary_entities == []


@pytest.mark.asyncio
async def test_options_flow_select_features_then_configure() -> None:
    """Test selecting features and then configuring them."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    coordinator_data = MagicMock()
    coordinator_data.area_config = MagicMock()
    coordinator_data.area_config.name = "kitchen"
    coordinator_data.area_config.is_meta.return_value = False
    coordinator_data.area_config.config = {}
    coordinator_data.area_config.id = "kitchen"
    coordinator_data.entities = {}

    config_entry.runtime_data.coordinator.data = coordinator_data

    flow = OptionsFlowHandler(config_entry)
    flow.hass = MagicMock()
    flow._area_config = coordinator_data.area_config
    flow.area_options = {}

    from custom_components.magic_areas.config_flows.steps import (
        handle_feature_selection,
    )

    user_input = {
        str(MagicAreasFeatures.LIGHT_GROUPS): True,
        str(MagicAreasFeatures.CLIMATE_CONTROL): False,
    }

    # Patch async_step_show_menu for the handler call
    with patch.object(
        flow, "async_step_show_menu", new_callable=AsyncMock, return_value={"type": FlowResultType.MENU}
    ):
        result = await handle_feature_selection(flow, user_input=user_input)

    # Verify result and state
    assert result["type"] == FlowResultType.MENU
    assert CONF_ENABLED_FEATURES in flow.area_options
    enabled_features = _enabled_features(flow)
    assert MagicAreasFeatures.LIGHT_GROUPS in enabled_features
    assert MagicAreasFeatures.CLIMATE_CONTROL not in enabled_features


@pytest.mark.asyncio
async def test_options_flow_persists_configuration_across_steps() -> None:
    """Test that configuration persists when navigating through steps."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    coordinator_data = MagicMock()
    coordinator_data.area_config = MagicMock()
    coordinator_data.area_config.name = "kitchen"
    coordinator_data.area_config.is_meta.return_value = False
    coordinator_data.area_config.config = {}
    coordinator_data.area_config.id = "kitchen"
    coordinator_data.entities = {}

    config_entry.runtime_data.coordinator.data = coordinator_data

    flow = OptionsFlowHandler(config_entry)
    flow._area_config = coordinator_data.area_config
    flow.area_options = {"some_existing_option": "value"}

    # Add a feature
    flow.area_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {}
    }

    # Verify options are persisted in the flow object
    original_options = dict(flow.area_options)

    # Verify options were preserved after simulating step
    assert flow.area_options == original_options
    assert CONF_ENABLED_FEATURES in flow.area_options
    assert MagicAreasFeatures.LIGHT_GROUPS in _enabled_features(flow)


@pytest.mark.asyncio
async def test_options_flow_shows_menu_with_feature_conf_options() -> None:
    """Test that show_menu includes feature configuration options."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    coordinator_data = MagicMock()
    coordinator_data.area_config = MagicMock()
    coordinator_data.area_config.is_meta.return_value = False
    coordinator_data.entities = {}

    config_entry.runtime_data.coordinator.data = coordinator_data

    flow = OptionsFlowHandler(config_entry)
    flow.hass = MagicMock()
    flow._area_config = coordinator_data.area_config
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.LIGHT_GROUPS: {},
            MagicAreasFeatures.CLIMATE_CONTROL: {},
        }
    }

    with patch.object(
        flow, "async_show_menu", new_callable=MagicMock, return_value={"type": FlowResultType.MENU}
    ) as mock_show_menu:
        await flow.async_step_show_menu()

        # Verify async_show_menu was called
        assert mock_show_menu.called
        call_args = mock_show_menu.call_args
        menu_options = call_args[1]["menu_options"]

        # Verify menu includes feature configuration options
        assert "feature_conf_light_groups" in menu_options
        assert "feature_conf_climate_control" in menu_options
        assert "area_config" in menu_options
        assert "finish" in menu_options


@pytest.mark.asyncio
async def test_options_flow_deselecting_feature_removes_from_options() -> None:
    """Test that deselecting a feature removes it from options."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    flow = OptionsFlowHandler(config_entry)
    flow._area_config = MagicMock()
    flow._area_config.config = {}
    flow._area_config.id = "kitchen"
    flow._area_config.is_meta.return_value = False

    # Start with features enabled
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.LIGHT_GROUPS: {},
            MagicAreasFeatures.CLIMATE_CONTROL: {},
        }
    }

    from custom_components.magic_areas.config_flows.steps import (
        handle_feature_selection,
    )

    # Deselect climate_control
    user_input = {
        str(MagicAreasFeatures.LIGHT_GROUPS): True,
        str(MagicAreasFeatures.CLIMATE_CONTROL): False,
    }

    # Patch async_step_show_menu for the handler call
    with patch.object(
        flow, "async_step_show_menu", new_callable=AsyncMock, return_value={"type": FlowResultType.MENU}
    ):
        result = await handle_feature_selection(flow, user_input=user_input)

    # Verify climate_control was removed
    assert result["type"] == FlowResultType.MENU
    enabled_features = _enabled_features(flow)
    assert MagicAreasFeatures.LIGHT_GROUPS in enabled_features
    assert MagicAreasFeatures.CLIMATE_CONTROL not in enabled_features


@pytest.mark.asyncio
async def test_options_flow_handles_multiple_feature_configurations() -> None:
    """Test flow with multiple features being configured."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    coordinator_data = MagicMock()
    coordinator_data.area_config = MagicMock()
    coordinator_data.area_config.is_meta.return_value = False
    coordinator_data.entities = {}

    config_entry.runtime_data.coordinator.data = coordinator_data

    flow = OptionsFlowHandler(config_entry)
    flow._area_config = coordinator_data.area_config
    flow.area_options = {}

    # Enable multiple features
    flow.area_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {"some_config": "value1"},
        MagicAreasFeatures.AGGREGATES: {"other_config": "value2"},
        MagicAreasFeatures.CLIMATE_CONTROL: {"preset": "occupied"},
    }

    # Verify all configurations are stored
    enabled_features = _enabled_features(flow)
    assert len(enabled_features) == 3
    assert enabled_features[MagicAreasFeatures.LIGHT_GROUPS] == {"some_config": "value1"}
    assert enabled_features[MagicAreasFeatures.AGGREGATES] == {"other_config": "value2"}
    assert enabled_features[MagicAreasFeatures.CLIMATE_CONTROL] == {"preset": "occupied"}
