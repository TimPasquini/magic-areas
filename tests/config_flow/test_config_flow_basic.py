"""Test basic Magic Areas config flow functionality.

This module contains tests for the basic form interactions and meta area creation
in the Magic Areas config flow.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import voluptuous as vol
from homeassistant import config_entries, setup
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, StateMachine
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.area_registry import AreaRegistry, async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.floor_registry import async_get as async_get_fr
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_constants import (
    AREA_STATE_EXTENDED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_META,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.area_maps import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
)
from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.config_flow import (
    ConfigBase,
    NullableEntitySelector,
    OptionsFlowHandler,
)
from custom_components.magic_areas.config_flows.feature_registry import (
    FeatureConfig,
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_ID,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.core_constants import (
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_WASP_IN_A_BOX,
)
from custom_components.magic_areas.schemas.features import CONFIGURABLE_FEATURES
from tests.const import MockAreaIds


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    area_registry.async_create(MockAreaIds.KITCHEN.value.capitalize())
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: MockAreaIds.KITCHEN.value.capitalize(),
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MockAreaIds.KITCHEN.value.capitalize()
    assert result2["data"][CONF_ID] == MockAreaIds.KITCHEN.value
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_floor_meta_area(hass: HomeAssistant) -> None:
    """Test we can create a floor-based meta area."""
    await setup.async_setup_component(hass, "config", {})

    # Create a floor
    floor_registry = async_get_fr(hass)
    floor = floor_registry.async_create("Ground Floor")
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    # Check that the floor is in the list of available areas
    assert f"(Meta) {floor.name}" in result["data_schema"].schema["name"].container

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: f"(Meta) {floor.name}",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == floor.name
    assert result2["data"][CONF_ID] == floor.floor_id
    assert result2["data"][CONF_TYPE] == AREA_TYPE_META
    assert len(mock_setup_entry.mock_calls) == 1


async def test_no_areas(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "config", {})

    # Create config entries for all meta areas to ensure they are filtered out
    for area_id in ["global", "interior", "exterior"]:
        MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ID: area_id,
                CONF_NAME: area_id.title(),
                CONF_TYPE: AREA_TYPE_META,
            },
            unique_id=area_id,
            state=ConfigEntryState.LOADED,
        ).add_to_hass(hass)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_more_areas"


async def test_area_already_configured(hass: HomeAssistant) -> None:
    """Test that an already-configured area is not an option."""
    await setup.async_setup_component(hass, "config", {})

    # Setup Kitchen
    area_registry = async_get_ar(hass)
    area_registry.async_create(MockAreaIds.KITCHEN.value.capitalize())

    # Create config entry for Kitchen
    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ID: MockAreaIds.KITCHEN.value,
            CONF_NAME: MockAreaIds.KITCHEN.value.capitalize(),
            CONF_TYPE: "interior",
        },
        unique_id=MockAreaIds.KITCHEN.value,
        state=ConfigEntryState.LOADED,
    ).add_to_hass(hass)

    # Create config entries for all meta areas to ensure they are filtered out
    for area_id in ["global", "interior", "exterior"]:
        MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ID: area_id,
                CONF_NAME: area_id.title(),
                CONF_TYPE: AREA_TYPE_META,
            },
            unique_id=area_id,
            state=ConfigEntryState.LOADED,
        ).add_to_hass(hass)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_more_areas"


async def test_invalid_area(hass: HomeAssistant) -> None:
    """Test we get the form and submit an invalid area."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    area_entry = area_registry.async_create(MockAreaIds.KITCHEN.value.capitalize())
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Delete area so it's invalid when configuring
    area_registry.async_delete(area_entry.id)
    await hass.async_block_till_done()

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: MockAreaIds.KITCHEN.value.capitalize(),
        },
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "invalid_area"


async def test_form_meta_area(hass: HomeAssistant) -> None:
    """Test we get the form and create a meta area."""
    await setup.async_setup_component(hass, "config", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: f"(Meta) {META_AREA_GLOBAL}",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == META_AREA_GLOBAL
    assert result2["data"][CONF_TYPE] == AREA_TYPE_META
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow_conflicting_meta_area(hass: HomeAssistant) -> None:
    """Test user flow when a meta area name is already taken by a regular area."""
    await setup.async_setup_component(hass, "config", {})

    area_registry = async_get_ar(hass)
    # Create an area named "Global" which conflicts with MetaAreaType.GLOBAL
    area_registry.async_create("Global")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM


def test_resolve_groups() -> None:
    """Test resolve_groups static method."""
    assert OptionsFlowHandler.resolve_groups(["a", ["b", "c"], "d"]) == [
        "a",
        "b",
        "c",
        "d",
    ]
    assert OptionsFlowHandler.resolve_groups(["a", "b", "a"]) == ["a", "b"]
