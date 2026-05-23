"""Tests for feature configuration step handler."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.data_entry_flow import FlowResultType
import voluptuous as vol

from custom_components.magic_areas.config_flows.steps import (
    handle_feature_conf,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
)


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
    """Test that the light-groups feature entry shows its submenu."""
    flow = MagicMock()
    flow._feature_step_id = f"feature_conf_{MagicAreasFeatures.LIGHT_GROUPS}"
    flow.context = {}
    flow.area_options = {}
    flow.async_show_menu = MagicMock(return_value={"type": FlowResultType.MENU})

    result = await handle_feature_conf(flow, user_input=None)

    assert result["type"] == FlowResultType.MENU
    flow.async_show_menu.assert_called_once()


@pytest.mark.asyncio
async def test_handle_feature_conf_with_known_feature() -> None:
    """Test that known light-group substeps are handled correctly."""
    flow = MagicMock()
    flow._feature_step_id = "feature_conf_light_groups_roles"
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
    flow._feature_step_id = "feature_conf_light_groups_roles"
    flow.context = {}
    flow.area_options = {}
    flow.async_step_feature_conf_light_groups = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    # Provide valid user input
    user_input: dict[str, str] = {}

    result = await handle_feature_conf(flow, user_input=user_input)

    # Should proceed to show_menu on valid input
    assert result["type"] == FlowResultType.MENU


@pytest.mark.asyncio
async def test_handle_feature_conf_stores_valid_feature_config() -> None:
    """Test that valid feature configuration is stored in area_options."""
    flow = MagicMock()
    flow._feature_step_id = "feature_conf_light_groups_roles"
    flow.context = {}
    flow.area_options = {}
    flow.async_step_feature_conf_light_groups = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )

    # Provide valid user input
    user_input: dict[str, str] = {}

    result = await handle_feature_conf(flow, user_input=user_input)

    # Should proceed to show_menu
    assert result["type"] == FlowResultType.MENU
    # Check that features dict was created
    assert "features" in flow.area_options


@pytest.mark.asyncio
async def test_handle_light_groups_manage_mode_uses_separate_all_lights_gate() -> None:
    """Manage mode exposes all-lights as a separate boolean gate."""
    flow = MagicMock()
    flow._feature_step_id = "feature_conf_light_groups_adaptive_lighting"
    flow.context = {}
    flow.all_lights = ["light.test_light"]
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.LIGHT_GROUPS.value: {
                CONF_OVERHEAD_LIGHTS: ["light.test_light"],
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
                ),
            }
        }
    }
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})
    flow._build_schema_from_vol = MagicMock(return_value={})

    result = await handle_feature_conf(flow, user_input=None)

    assert result["type"] == FlowResultType.FORM
    schema = flow._build_schema_from_vol.call_args.args[0]
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL in keys
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES in keys
    role_marker = next(
        marker
        for marker in schema.schema
        if getattr(marker, "schema", marker)
        == CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES
    )
    assert schema.schema[role_marker]([CONF_OVERHEAD_LIGHTS]) == [CONF_OVERHEAD_LIGHTS]
    with pytest.raises(vol.Invalid):
        schema.schema[role_marker](["all_lights"])


@pytest.mark.asyncio
async def test_handle_light_groups_preserves_hidden_manage_all_lights_gate() -> None:
    """Editing visible light options should preserve hidden room-level AL gate."""
    flow = MagicMock()
    flow._feature_step_id = "feature_conf_light_groups_adaptive_lighting"
    flow.context = {}
    flow.area_options = {
        CONF_ENABLED_FEATURES: {
            MagicAreasFeatures.LIGHT_GROUPS.value: {
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
                ),
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL: True,
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES: [CONF_OVERHEAD_LIGHTS],
            }
        }
    }
    flow.async_step_feature_conf_light_groups = AsyncMock(
        return_value={"type": FlowResultType.MENU}
    )
    flow.async_show_form = MagicMock(return_value={"type": FlowResultType.FORM})

    result = await handle_feature_conf(
        flow,
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            )
        },
    )

    feature_options = flow.area_options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS.value
    ]
    assert result["type"] == FlowResultType.FORM
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] == [
        CONF_OVERHEAD_LIGHTS
    ]
