"""Tests for advanced feature configuration handler covering uncovered edge cases.

Tests verify the feature configuration handler correctly handles:
- Schema validation with error handling (vol.MultipleInvalid)
- merge_options flag (merge vs replace)
- next_step routing to follow-up config flow steps
"""

import pytest
import voluptuous as vol
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.magic_areas.config_flows.steps.feature_config_advanced import (
    handle_feature_conf_advanced,
)
from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.enums import MagicAreasFeatures


@pytest.fixture
def mock_options_flow() -> MagicMock:
    """Create a mock OptionsFlowHandler."""
    flow = MagicMock()
    flow.area_options = {}
    flow.async_abort = MagicMock()
    flow.async_show_form = MagicMock()
    flow.async_step_show_menu = AsyncMock()
    flow._build_options_schema = MagicMock(return_value=vol.Schema({}))
    return flow


@pytest.mark.asyncio
async def test_invalid_schema_returns_error(mock_options_flow: MagicMock) -> None:
    """Verify vol.MultipleInvalid caught and returned as error (lines 62-63)."""
    feature_key = MagicAreasFeatures.LIGHT_GROUPS

    # Create invalid user input that will fail schema validation
    user_input = {"invalid_key": "invalid_value"}

    # Patch the feature schema to raise vol.MultipleInvalid
    with patch.object(
        FEATURE_REGISTRY[feature_key],
        "schema",
        side_effect=vol.MultipleInvalid([vol.Invalid("Test error")]),
    ):
        await handle_feature_conf_advanced(
            mock_options_flow, feature_key, user_input
        )

    # Verify errors were set
    mock_options_flow.async_show_form.assert_called_once()
    call_kwargs = mock_options_flow.async_show_form.call_args[1]
    assert "errors" in call_kwargs
    assert call_kwargs["errors"] == {"base": "invalid_input"}


@pytest.mark.asyncio
async def test_merge_options_true_merges_into_existing(
    mock_options_flow: MagicMock,
) -> None:
    """Verify merge_options flag updates existing feature config (line 67)."""
    feature_key = MagicAreasFeatures.AGGREGATES

    # Set up existing feature config
    mock_options_flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.AGGREGATES: {"existing_key": "existing_value"}
        }
    }

    # Create valid user input
    user_input = {"new_key": "new_value"}

    # Find a feature with merge_options=True (or patch one)
    feature = FEATURE_REGISTRY[feature_key]
    with patch.object(
        feature, "merge_options", True
    ), patch.object(
        feature, "schema", return_value=user_input
    ), patch.object(
        feature, "next_step", None
    ):
        await handle_feature_conf_advanced(
            mock_options_flow, feature_key, user_input
        )

    # Verify merged config contains both existing and new keys
    merged_config = mock_options_flow.area_options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.AGGREGATES
    ]
    assert merged_config.get("existing_key") == "existing_value"
    assert merged_config.get("new_key") == "new_value"


@pytest.mark.asyncio
async def test_merge_options_false_replaces(mock_options_flow: MagicMock) -> None:
    """Verify merge_options flag replaces feature config (line 69)."""
    feature_key = MagicAreasFeatures.LIGHT_GROUPS

    # Set up existing feature config
    mock_options_flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.LIGHT_GROUPS: {"old_key": "old_value"}
        }
    }

    # Create valid user input
    user_input = {"new_key": "new_value"}

    # Find a feature with merge_options=False (or patch one)
    feature = FEATURE_REGISTRY[feature_key]
    with patch.object(
        feature, "merge_options", False
    ), patch.object(
        feature, "schema", return_value=user_input
    ), patch.object(
        feature, "next_step", None
    ):
        await handle_feature_conf_advanced(
            mock_options_flow, feature_key, user_input
        )

    # Verify config was replaced, not merged
    new_config = mock_options_flow.area_options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ]
    assert "old_key" not in new_config
    assert new_config.get("new_key") == "new_value"


@pytest.mark.asyncio
async def test_next_step_routing(mock_options_flow: MagicMock) -> None:
    """Verify next_step routes to next flow step (line 73)."""
    feature_key = MagicAreasFeatures.CLIMATE_CONTROL

    # Create valid user input
    user_input = {"preset_occupied": "none", "preset_clear": "away"}

    # Set up next_step on the feature
    feature = FEATURE_REGISTRY[feature_key]
    next_step = "feature_conf_climate_control_select_presets"

    with patch.object(
        feature, "schema", return_value=user_input
    ), patch.object(
        feature, "next_step", next_step
    ), patch.object(
        feature, "merge_options", False
    ):
        # Mock the async_step_* method that should be called
        async_step_method = AsyncMock()
        setattr(
            mock_options_flow,
            f"async_step_{next_step}",
            async_step_method,
        )

        await handle_feature_conf_advanced(
            mock_options_flow, feature_key, user_input
        )

    # Verify next_step method was called
    async_step_method.assert_called_once()
