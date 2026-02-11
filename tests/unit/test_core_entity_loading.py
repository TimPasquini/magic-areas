"""Unit tests for entity loading core module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.entity_loading import (
    load_area_entities,
    load_meta_area_entities,
)


@pytest.mark.asyncio
async def test_load_area_entities_with_no_entities(hass: HomeAssistant) -> None:
    """Test load_area_entities with empty area."""
    # Mock the registries
    mock_entity_registry = MagicMock()
    mock_entity_registry.entities.get_entries_for_area_id.return_value = []
    mock_device_registry = MagicMock()
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.devicereg_async_get",
        return_value=mock_device_registry,
    ):
        entities, magic_entities = await load_area_entities(
            hass, "test_area", "test_config", {}
        )

    # Should return empty dictionaries
    assert entities == {}
    assert magic_entities == {}


@pytest.mark.asyncio
async def test_load_area_entities_with_include_list(hass: HomeAssistant) -> None:
    """Test load_area_entities respects CONF_INCLUDE_ENTITIES."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    # Setup: no area entities, but include list has entities
    mock_entity_registry.entities.get_entries_for_area_id.return_value = []
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    # Create mock included entity
    included_entity = MagicMock()
    included_entity.disabled = False
    included_entity.config_entry_id = None
    included_entity.entity_id = "light.included"
    included_entity.domain = "light"
    included_entity.entity_category = None

    mock_entity_registry.async_get.return_value = included_entity

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.devicereg_async_get",
        return_value=mock_device_registry,
    ):
        entities, magic_entities = await load_area_entities(
            hass,
            "test_area",
            "test_config",
            {"include_entities": ["light.included"]},
        )

    # Verify included entity was added
    assert "light" in entities
    assert any(e["entity_id"] == "light.included" for e in entities["light"])


@pytest.mark.asyncio
async def test_load_area_entities_excludes_our_config_entry(
    hass: HomeAssistant,
) -> None:
    """Test that entities from our config entry are excluded."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    config_entry_id = "our_config"

    # Create entity from our config entry (should be excluded)
    our_entity = MagicMock()
    our_entity.disabled = False
    our_entity.config_entry_id = config_entry_id
    our_entity.entity_id = "light.our_entity"
    our_entity.domain = "light"
    our_entity.entity_category = None

    mock_entity_registry.entities.get_entries_for_area_id.return_value = [our_entity]
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.devicereg_async_get",
        return_value=mock_device_registry,
    ):
        entities, magic_entities = await load_area_entities(
            hass, "test_area", config_entry_id, {}
        )

    # Entity from our config should be excluded
    assert entities == {}


@pytest.mark.asyncio
async def test_load_area_entities_with_exclude_list(hass: HomeAssistant) -> None:
    """Test load_area_entities respects CONF_EXCLUDE_ENTITIES."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    excluded_entity = MagicMock()
    excluded_entity.disabled = False
    excluded_entity.config_entry_id = None
    excluded_entity.entity_id = "light.excluded"
    excluded_entity.domain = "light"
    excluded_entity.entity_category = None

    normal_entity = MagicMock()
    normal_entity.disabled = False
    normal_entity.config_entry_id = None
    normal_entity.entity_id = "light.normal"
    normal_entity.domain = "light"
    normal_entity.entity_category = None

    mock_entity_registry.entities.get_entries_for_area_id.return_value = [
        excluded_entity,
        normal_entity,
    ]
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.devicereg_async_get",
        return_value=mock_device_registry,
    ):
        entities, magic_entities = await load_area_entities(
            hass,
            "test_area",
            "test_config",
            {"exclude_entities": ["light.excluded"]},
        )

    # Excluded entity should not be in result
    all_entity_ids = [e["entity_id"] for e in entities.get("light", [])]
    assert "light.excluded" not in all_entity_ids
    assert "light.normal" in all_entity_ids


@pytest.mark.asyncio
async def test_load_meta_area_entities_empty(hass: HomeAssistant) -> None:
    """Test load_meta_area_entities with no child areas."""
    mock_entity_registry = MagicMock()

    # Mock hass.config_entries to return empty list
    hass.config_entries.async_entries = MagicMock(return_value=[])

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ):
        entities, magic_entities = await load_meta_area_entities(
            hass, [], "test_config", {}
        )

    # Should return empty results for empty child areas
    assert entities == {}
    assert magic_entities == {}


@pytest.mark.asyncio
async def test_load_meta_area_entities_with_child_areas(hass: HomeAssistant) -> None:
    """Test load_meta_area_entities collects entities from child areas."""
    from homeassistant.config_entries import ConfigEntryState

    mock_entity_registry = MagicMock()

    # Create mock child area entities
    child_entity = MagicMock()
    child_entity.disabled = False
    child_entity.config_entry_id = "child_config"
    child_entity.entity_id = "sensor.child_area_temp"
    child_entity.domain = "sensor"
    child_entity.entity_category = None

    mock_entity_registry.entities.get_entries_for_config_entry_id.return_value = [
        child_entity
    ]

    # Create mock config entry for child area
    mock_child_entry = MagicMock()
    mock_child_entry.state = ConfigEntryState.LOADED
    mock_child_entry.domain = "magic_areas"
    mock_child_entry.entry_id = "child_config"
    mock_child_entry.runtime_data.area.slug = "bedroom"

    # Mock async_entries to return our mock entry
    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch.object(
        hass.config_entries, "async_entries", return_value=[mock_child_entry]
    ):
        entities, magic_entities = await load_meta_area_entities(
            hass, ["bedroom"], "parent_config", {}
        )

    # Should collect entities from the child area
    assert "sensor" in entities
    assert len(entities["sensor"]) > 0


@pytest.mark.asyncio
async def test_load_meta_area_entities_respects_exclude_list(
    hass: HomeAssistant,
) -> None:
    """Test load_meta_area_entities respects CONF_EXCLUDE_ENTITIES."""
    from homeassistant.config_entries import ConfigEntryState

    mock_entity_registry = MagicMock()

    # Create mock child area entities
    excluded_entity = MagicMock()
    excluded_entity.entity_id = "sensor.excluded"
    excluded_entity.domain = "sensor"

    included_entity = MagicMock()
    included_entity.entity_id = "sensor.included"
    included_entity.domain = "sensor"

    mock_entity_registry.entities.get_entries_for_config_entry_id.return_value = [
        excluded_entity,
        included_entity,
    ]

    # Create mock config entry
    mock_child_entry = MagicMock()
    mock_child_entry.state = ConfigEntryState.LOADED
    mock_child_entry.domain = "magic_areas"
    mock_child_entry.entry_id = "child_config"
    mock_child_entry.runtime_data.area.slug = "bedroom"

    with patch(
        "custom_components.magic_areas.core.entity_loading.entityreg_async_get",
        return_value=mock_entity_registry,
    ), patch.object(
        hass.config_entries, "async_entries", return_value=[mock_child_entry]
    ):
        entities, magic_entities = await load_meta_area_entities(
            hass,
            ["bedroom"],
            "parent_config",
            {"exclude_entities": ["sensor.excluded"]},
        )

    # Excluded entity should not be in result
    if "sensor" in entities:
        entity_ids = [e.get("entity_id") for e in entities.get("sensor", [])]
        assert "sensor.excluded" not in entity_ids
