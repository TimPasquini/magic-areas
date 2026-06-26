"""Test basic Magic Areas config flow functionality.

This module contains tests for the basic form interactions and meta area creation
in the Magic Areas config flow.
"""

from unittest.mock import patch


from homeassistant import config_entries, setup
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.floor_registry import async_get as async_get_fr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import (
    AreaType,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_ID,
    CONF_TYPE,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
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
    assert result["data_schema"] is not None
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
    assert result2["data"][CONF_TYPE] == AreaType.META
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
                CONF_TYPE: AreaType.META,
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
                CONF_TYPE: AreaType.META,
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
    assert result2["data"][CONF_TYPE] == AreaType.META
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
    from custom_components.magic_areas.config_flows import (
        ConfigFlowEntityGatherer,
    )

    assert ConfigFlowEntityGatherer.resolve_groups(["a", ["b", "c"], "d"]) == [
        "a",
        "b",
        "c",
        "d",
    ]
    assert ConfigFlowEntityGatherer.resolve_groups(["a", "b", "a"]) == ["a", "b"]


async def test_gather_all_entities_includes_registry_entries_without_state(
    hass: HomeAssistant,
) -> None:
    """Gatherer should include registry-backed entities even before state exists."""
    from custom_components.magic_areas.config_flows import (
        ConfigFlowEntityGatherer,
    )

    entity_registry = async_get_er(hass)
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="registry_only_sensor",
        suggested_object_id="registry_only_sensor",
    )
    await hass.async_block_till_done()

    gatherer = ConfigFlowEntityGatherer(
        hass, entities_by_domain={}, config_entry_options={}
    )
    all_entities = gatherer.gather_all_entities()

    assert "sensor.registry_only_sensor" in all_entities
