"""Tests for dynamic step routing in options flow."""

from collections.abc import Awaitable, Callable, Mapping
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.config_entries import ConfigFlowResult

from custom_components.magic_areas.config_flows import OptionsFlowHandler


@pytest.mark.asyncio
async def test_options_flow_routes_feature_conf_step() -> None:
    """Test that async_step routes feature_conf_* patterns."""
    config_entry: MagicMock = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    flow = OptionsFlowHandler(config_entry)

    with patch.object(
        flow,
        "async_step_feature_conf",
        new_callable=AsyncMock,
        return_value={"type": "form"},
    ) as mock_handler:
        result = await flow.async_step("feature_conf_light_groups", user_input=None)

        # Verify async_step_feature_conf was called
        mock_handler.assert_called_once_with(None)
        assert result["type"] == "form"


@pytest.mark.asyncio
async def test_options_flow_dynamic_step_attribute_routes_feature_conf() -> None:
    """HA-style dynamic step attributes should route through generic dispatch."""
    config_entry: MagicMock = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}
    flow = OptionsFlowHandler(config_entry)

    with patch.object(
        flow, "async_step", new_callable=AsyncMock, return_value={"type": "form"}
    ) as mock_router:
        step = cast(
            Callable[
                [Mapping[str, object] | None],
                Awaitable[ConfigFlowResult],
            ],
            flow.async_step_feature_conf_light_groups,
        )
        result = await step({"enabled": True})

    mock_router.assert_awaited_once_with("feature_conf_light_groups", {"enabled": True})
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_options_flow_sets_feature_step_id_on_routing() -> None:
    """Test that _feature_step_id is set when routing feature_conf_* steps."""
    config_entry: MagicMock = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    flow = OptionsFlowHandler(config_entry)

    with patch.object(
        flow,
        "async_step_feature_conf",
        new_callable=AsyncMock,
        return_value={"type": "form"},
    ) as mock_handler:
        await flow.async_step(
            "feature_conf_climate_control", user_input={"test": "input"}
        )

        # Verify _feature_step_id was set
        assert flow._feature_step_id == "feature_conf_climate_control"
        # Verify step_id was extracted correctly by checking the call
        mock_handler.assert_called_once_with({"test": "input"})


@pytest.mark.asyncio
async def test_options_flow_raises_on_unknown_step() -> None:
    """Test that unknown step_id raises ValueError."""
    config_entry: MagicMock = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    flow = OptionsFlowHandler(config_entry)

    # This should raise when awaited
    with pytest.raises(ValueError) as exc_info:
        await flow.async_step("unknown_step", user_input=None)

    assert "Unknown step unknown_step" in str(exc_info.value)


@pytest.mark.asyncio
async def test_options_flow_routes_multiple_feature_steps() -> None:
    """Test that multiple feature_conf_* steps are routed correctly."""
    config_entry: MagicMock = MagicMock()
    config_entry.entry_id = "test_entry"
    config_entry.options = {}

    flow = OptionsFlowHandler(config_entry)

    with patch.object(
        flow,
        "async_step_feature_conf",
        new_callable=AsyncMock,
        return_value={"type": "form"},
    ) as mock_handler:
        # Test multiple different feature steps
        steps = [
            "feature_conf_light_groups",
            "feature_conf_climate_control",
            "feature_conf_aggregates",
        ]

        for step_id in steps:
            flow._feature_step_id = None  # Reset
            mock_handler.reset_mock()
            result = await flow.async_step(step_id, user_input=None)

            assert flow._feature_step_id == step_id
            assert result["type"] == "form"
