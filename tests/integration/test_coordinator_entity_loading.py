"""Coordinator entity-loading contract tests."""

from typing import cast

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_registry

from custom_components.magic_areas.components import MAGIC_AREAS_COMPONENTS
from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.config_keys.area import (
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
)
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)


def _all_loaded_entity_ids(coordinator: MagicAreasCoordinator) -> list[str]:
    """Collect loaded entity ids from a coordinator snapshot."""
    ids: list[str] = []
    for domain_entities in coordinator.data.entities.values():
        ids.extend(
            entity_id
            for entity in domain_entities
            if (entity_id := entity.get("entity_id")) is not None
        )
    return ids


def _set_include_entities(config_entry: MockConfigEntry, hass: HomeAssistant, entity_ids: list[str]) -> None:
    """Update include-entities config on a mock config entry."""
    data = dict(config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = entity_ids
    hass.config_entries.async_update_entry(config_entry, data=data)


def _set_include_exclude_entities(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
    *,
    include_entity_ids: list[str],
    exclude_entity_ids: list[str],
) -> None:
    """Update include/exclude entity config on a mock config entry."""
    data = dict(config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = include_entity_ids
    data[CONF_EXCLUDE_ENTITIES] = exclude_entity_ids
    hass.config_entries.async_update_entry(config_entry, data=data)


async def _init_and_get_coordinator(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> MagicAreasCoordinator:
    """Initialize integration for a single config entry and return coordinator."""
    await init_integration_helper(hass, [config_entry])
    await hass.async_block_till_done()
    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    return cast(MagicAreasCoordinator, entry.runtime_data.coordinator)


async def test_magic_area_include_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Entities listed in include_entities are loaded into snapshot."""
    entity_registry = mock_registry(hass)
    external_entity = entity_registry.async_get_or_create("switch", "test", "external_switch")

    _set_include_entities(mock_config_entry, hass, [external_entity.entity_id])

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    assert "switch" in coordinator.data.entities
    loaded_ids = [entity["entity_id"] for entity in coordinator.data.entities["switch"]]
    assert external_entity.entity_id in loaded_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_disabled(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Disabled registry entries are excluded from loaded entities."""
    entity_registry = mock_registry(hass)
    disabled = entity_registry.async_get_or_create(
        "light",
        "test",
        "disabled_light",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    normal = entity_registry.async_get_or_create("light", "test", "normal_light")

    _set_include_entities(mock_config_entry, hass, [disabled.entity_id, normal.entity_id])
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert disabled.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_diagnostic(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Diagnostic-category entities are excluded from loaded entities."""
    entity_registry = mock_registry(hass)
    diagnostic = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "diag_sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    normal = entity_registry.async_get_or_create("sensor", "test", "normal_sensor")

    _set_include_entities(mock_config_entry, hass, [diagnostic.entity_id, normal.entity_id])
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert diagnostic.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_includes_normal_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Normal entities across domains remain includable."""
    entity_registry = mock_registry(hass)
    light_entity = entity_registry.async_get_or_create("light", "test", "test_light")
    sensor_entity = entity_registry.async_get_or_create("sensor", "test", "test_sensor")
    switch_entity = entity_registry.async_get_or_create("switch", "test", "test_switch")

    _set_include_entities(
        mock_config_entry,
        hass,
        [light_entity.entity_id, sensor_entity.entity_id, switch_entity.entity_id],
    )
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert light_entity.entity_id in all_entity_ids
    assert sensor_entity.entity_id in all_entity_ids
    assert switch_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_excluded_entities_respected(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """exclude_entities wins over explicit include_entities."""
    entity_registry = mock_registry(hass)
    excluded_entity = entity_registry.async_get_or_create("light", "test", "excluded_light")
    included_entity = entity_registry.async_get_or_create("light", "test", "included_light")

    _set_include_exclude_entities(
        mock_config_entry,
        hass,
        include_entity_ids=[excluded_entity.entity_id, included_entity.entity_id],
        exclude_entity_ids=[excluded_entity.entity_id],
    )
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert excluded_entity.entity_id not in all_entity_ids
    assert included_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_coordinator_entity_loading(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator snapshot includes selected include_entities entries."""
    entity_registry = mock_registry(hass)
    light1 = entity_registry.async_get_or_create("light", "test", "light1")
    light2 = entity_registry.async_get_or_create("light", "test", "light2")
    sensor1 = entity_registry.async_get_or_create("sensor", "test", "sensor1")

    _set_include_entities(mock_config_entry, hass, [light1.entity_id, light2.entity_id, sensor1.entity_id])
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    assert coordinator.data is not None
    assert "light" in coordinator.data.entities
    assert "sensor" in coordinator.data.entities

    light_ids = [e.get("entity_id") for e in coordinator.data.entities["light"]]
    sensor_ids = [e.get("entity_id") for e in coordinator.data.entities["sensor"]]

    assert light1.entity_id in light_ids
    assert light2.entity_id in light_ids
    assert sensor1.entity_id in sensor_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_loads_device_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Entities linked by device-in-area relationship are loaded."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_id = entry.runtime_data.coordinator._area_config.id

    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("test", "test_device_1")},
    )
    device_registry.async_update_device(device.id, area_id=area_id)

    entity = entity_registry.async_get_or_create("light", "test", "device_light", device_id=device.id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_respects_config_entry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Entities owned by magic_areas config entry are not self-ingested."""
    entity_registry = er.async_get(hass)

    our_entity = entity_registry.async_get_or_create(
        "binary_sensor",
        "magic_areas",
        "our_area_state",
        config_entry=mock_config_entry,
    )
    normal_entity = entity_registry.async_get_or_create("light", "test", "other_light")

    _set_include_entities(mock_config_entry, hass, [our_entity.entity_id, normal_entity.entity_id])
    coordinator = await _init_and_get_coordinator(hass, mock_config_entry)

    all_entity_ids = _all_loaded_entity_ids(coordinator)
    assert our_entity.entity_id not in all_entity_ids
    assert normal_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_available_platforms(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Area config exposes supported platforms via coordinator snapshot."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator.data.area_config

    assert area_config.available_platforms() == MAGIC_AREAS_COMPONENTS

    await shutdown_integration(hass, [mock_config_entry])


async def test_config_entry_update_pattern(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """HA config-entry updates propagate to runtime entry data."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    assert mock_config_entry.data[CONF_INCLUDE_ENTITIES] == []

    new_data = dict(mock_config_entry.data)
    new_data[CONF_INCLUDE_ENTITIES] = ["light.new_light"]
    hass.config_entries.async_update_entry(mock_config_entry, data=new_data)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    assert entry.data[CONF_INCLUDE_ENTITIES] == ["light.new_light"]

    await shutdown_integration(hass, [mock_config_entry])
