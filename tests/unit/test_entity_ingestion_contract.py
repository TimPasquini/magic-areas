"""Contract tests for entity ingestion public API and behavior parity."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys import (
    CONF_EXCLUDE_ENTITIES,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core import entity_loading
from custom_components.magic_areas.core.entity_loading.filters import (
    should_exclude_entity,
)
from custom_components.magic_areas.core.snapshot_builder import build_snapshot


def test_entity_loading_public_api_exports() -> None:
    """Public API exports expected loader entry points."""
    assert callable(entity_loading.load_area_entities)
    assert callable(entity_loading.load_meta_area_entities)
    assert "load_area_entities" in entity_loading.__all__
    assert "load_meta_area_entities" in entity_loading.__all__
    assert not hasattr(entity_loading, "filter_entity_list")


def test_should_exclude_entity_parity_config_and_diagnostic() -> None:
    """CONFIG and DIAGNOSTIC categories remain excluded by default."""
    config_entity = MagicMock()
    config_entity.config_entry_id = "different_config"
    config_entity.disabled = False
    config_entity.entity_id = "number.test"
    config_entity.entity_category = EntityCategory.CONFIG

    diagnostic_entity = MagicMock()
    diagnostic_entity.config_entry_id = "different_config"
    diagnostic_entity.disabled = False
    diagnostic_entity.entity_id = "sensor.test"
    diagnostic_entity.entity_category = EntityCategory.DIAGNOSTIC

    assert should_exclude_entity(config_entity, "our_config") is True
    assert should_exclude_entity(diagnostic_entity, "our_config") is True


@pytest.mark.asyncio
async def test_load_area_entities_parity_include_shape(
    hass: HomeAssistant,
) -> None:
    """Included entities remain present in the expected grouped shape."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    mock_entity_registry.entities.get_entries_for_area_id.return_value = []
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    included_entity = MagicMock()
    included_entity.disabled = False
    included_entity.config_entry_id = None
    included_entity.entity_id = "light.contract_included"
    included_entity.domain = "light"
    included_entity.entity_category = None
    included_entity.original_device_class = None
    included_entity.unit_of_measurement = None
    mock_entity_registry.async_get.return_value = included_entity

    with patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_entity_registry",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_device_registry",
        return_value=mock_device_registry,
    ):
        entities, magic_entities = await entity_loading.load_area_entities(
            hass,
            "test_area",
            "test_config",
            {"include_entities": ["light.contract_included"]},
        )

    assert magic_entities == {}
    assert "light" in entities
    assert entities["light"][0]["entity_id"] == "light.contract_included"


@pytest.mark.asyncio
async def test_load_meta_area_entities_parity_shape(
    hass: HomeAssistant,
) -> None:
    """Meta-area loading keeps grouped output shape for child entities."""
    from homeassistant.config_entries import ConfigEntryState

    mock_entity_registry = MagicMock()
    child_entity = MagicMock()
    child_entity.entity_id = "sensor.child_temp"
    child_entity.domain = "sensor"
    mock_entity_registry.entities.get_entries_for_config_entry_id.return_value = [
        child_entity
    ]

    mock_child_entry = MagicMock()
    mock_child_entry.state = ConfigEntryState.LOADED
    mock_child_entry.domain = "magic_areas"
    mock_child_entry.entry_id = "child_config"
    mock_child_entry.runtime_data.coordinator.data.area_config.slug = "bedroom"

    with patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_entity_registry",
        return_value=mock_entity_registry,
    ), patch.object(hass.config_entries, "async_entries", return_value=[mock_child_entry]):
        entities, magic_entities = await entity_loading.load_meta_area_entities(
            hass,
            ["bedroom"],
            "parent_config",
            {},
        )

    assert magic_entities == {}
    assert "sensor" in entities
    assert entities["sensor"][0]["entity_id"] == "sensor.child_temp"


@pytest.mark.asyncio
async def test_load_area_entities_include_exclude_precedence(
    hass: HomeAssistant,
) -> None:
    """Exclude list takes precedence over include list."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    mock_entity_registry.entities.get_entries_for_area_id.return_value = []
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    included_and_excluded = MagicMock()
    included_and_excluded.disabled = False
    included_and_excluded.config_entry_id = None
    included_and_excluded.entity_id = "light.conflict"
    included_and_excluded.domain = "light"
    included_and_excluded.entity_category = None
    included_and_excluded.original_device_class = None
    included_and_excluded.unit_of_measurement = None
    mock_entity_registry.async_get.return_value = included_and_excluded

    with patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_entity_registry",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_device_registry",
        return_value=mock_device_registry,
    ):
        entities, _magic_entities = await entity_loading.load_area_entities(
            hass,
            "test_area",
            "test_config",
            {
                CONF_INCLUDE_ENTITIES: ["light.conflict"],
                CONF_EXCLUDE_ENTITIES: ["light.conflict"],
            },
        )

    assert entities == {}


@pytest.mark.asyncio
async def test_load_area_entities_diagnostic_toggle_parity(
    hass: HomeAssistant,
) -> None:
    """Diagnostic/config exclusion follows loader-level toggle."""
    mock_entity_registry = MagicMock()
    mock_device_registry = MagicMock()

    diagnostic_entity = MagicMock()
    diagnostic_entity.disabled = False
    diagnostic_entity.config_entry_id = None
    diagnostic_entity.entity_id = "sensor.diag"
    diagnostic_entity.domain = "sensor"
    diagnostic_entity.entity_category = EntityCategory.DIAGNOSTIC
    diagnostic_entity.original_device_class = None
    diagnostic_entity.unit_of_measurement = None

    normal_entity = MagicMock()
    normal_entity.disabled = False
    normal_entity.config_entry_id = None
    normal_entity.entity_id = "sensor.normal"
    normal_entity.domain = "sensor"
    normal_entity.entity_category = None
    normal_entity.original_device_class = None
    normal_entity.unit_of_measurement = None

    mock_entity_registry.entities.get_entries_for_area_id.return_value = [
        diagnostic_entity,
        normal_entity,
    ]
    mock_device_registry.devices.get_devices_for_area_id.return_value = []

    with patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_entity_registry",
        return_value=mock_entity_registry,
    ), patch(
        "custom_components.magic_areas.core.entity_loading.loader.get_device_registry",
        return_value=mock_device_registry,
    ):
        entities_ignore_true, _ = await entity_loading.load_area_entities(
            hass,
            "test_area",
            "test_config",
            {CONF_IGNORE_DIAGNOSTIC_ENTITIES: True},
        )
        entities_ignore_false, _ = await entity_loading.load_area_entities(
            hass,
            "test_area",
            "test_config",
            {CONF_IGNORE_DIAGNOSTIC_ENTITIES: False},
        )

    ids_true = [entity["entity_id"] for entity in entities_ignore_true.get("sensor", [])]
    ids_false = [entity["entity_id"] for entity in entities_ignore_false.get("sensor", [])]
    assert "sensor.diag" not in ids_true
    assert "sensor.normal" in ids_true
    assert "sensor.diag" in ids_false
    assert "sensor.normal" in ids_false


@pytest.mark.asyncio
async def test_snapshot_builder_entity_ingestion_integration_parity(
    hass: HomeAssistant,
) -> None:
    """Snapshot builder consumes entity-loading package with expected output parity."""
    area_config = AreaConfig(
        id="test_area",
        name="Test Area",
        slug="test_area",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=MockConfigEntry(domain="magic_areas", title="Test Area"),
    )

    async def _load_entities(*args: object, **kwargs: object) -> tuple[dict, dict]:
        return (
            {"sensor": [{"entity_id": "sensor.room_temp", "device_class": "temperature"}]},
            {"sensor": [{"entity_id": "sensor.magic_area_temp"}]},
        )

    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = None
    mock_registry.entities.values.return_value = []

    with patch(
        "custom_components.magic_areas.core.snapshot_builder.load_area_entities",
        side_effect=_load_entities,
    ), patch(
        "custom_components.magic_areas.core.snapshot_builder.er.async_get",
        return_value=mock_registry,
    ):
        snapshot = await build_snapshot(
            hass=hass,
            area_config=area_config,
            config_entry_id="entry_id",
        )

    assert "sensor" in snapshot.entities
    assert snapshot.entities["sensor"][0]["entity_id"] == "sensor.room_temp"
    assert "sensor" in snapshot.magic_entities
    assert snapshot.magic_entities["sensor"][0]["entity_id"] == "sensor.magic_area_temp"
