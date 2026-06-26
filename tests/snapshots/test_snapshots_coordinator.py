"""Snapshot tests for Magic Areas coordinator.

Tests coordinator data snapshots with realistic data including entity grouping,
presence sensor configuration, and feature enabling. Tests verify that the
coordinator correctly structures data for platforms.
"""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.coordinator import (
    MagicAreasData,
)


def _string_config_list(data: MagicAreasData, key: str) -> list[str]:
    """Return one config entry as a normalized list[str] for snapshot assertions."""
    value = data.config.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


@pytest.mark.asyncio
async def test_coordinator_basic_kitchen_area(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test coordinator snapshot for kitchen area with default config.

    Validates that the coordinator builds the correct data structure for
    a basic interior area with default presence device classes.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Snapshot complete coordinator data structure
    data_snapshot = {
        "area_id": data.area_config.slug,
        "area_name": data.area_config.name,
        "area_type": str(data.area_config.area_type),
        "is_meta": data.area_config.is_meta(),
        "config_keys": sorted(data.config.keys()),
        "enabled_features": sorted(data.enabled_features),
        "feature_config_keys": sorted(data.feature_configs.keys()),
        "presence_sensor_count": len(data.presence_sensors),
        "presence_sensors": sorted(data.presence_sensors),
        "presence_device_classes": sorted(
            _string_config_list(data, CONF_PRESENCE_SENSOR_DEVICE_CLASS)
        ),
        "entity_domains": sorted(data.entities.keys()),
        "entity_domain_counts": {
            domain: len(entities) for domain, entities in data.entities.items()
        },
        "magic_entity_domains": sorted(data.magic_entities.keys()),
        "magic_entity_counts": {
            domain: len(entities) for domain, entities in data.magic_entities.items()
        },
        "available": data.area_runtime.last_update_success,
    }

    assert data_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_with_all_areas(
    hass: HomeAssistant,
    snapshot_integration_all_areas: list[MockConfigEntry],
    snapshot: SnapshotAssertion,
) -> None:
    """Test coordinator snapshot with all areas including meta areas.

    Validates coordinator behavior when multiple areas (regular + meta)
    are initialized. Checks that meta areas have correct structure.
    """
    entries = snapshot_integration_all_areas

    meta_entry = None
    for entry in entries:
        coordinator = entry.runtime_data.coordinator
        if coordinator.data and coordinator.data.area_config.is_meta():
            meta_entry = entry
            break

    assert meta_entry is not None
    data: MagicAreasData = meta_entry.runtime_data.coordinator.data
    assert data is not None

    # Snapshot multi-area setup structure
    area_snapshot = {
        "area_id": data.area_config.slug,
        "area_name": data.area_config.name,
        "is_meta": data.area_config.is_meta(),
        "child_areas": sorted(data.child_areas),
        "child_area_count": len(data.child_areas),
        "presence_sensor_count": len(data.presence_sensors),
        "entity_domains": sorted(data.entities.keys()),
    }

    assert area_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_data_structure_fields(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that coordinator data contains all required fields.

    Validates that MagicAreasData snapshot has all expected fields
    with correct types for use by platforms.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Verify all required fields exist and have correct types
    field_validation = {
        "has_area_config": data.area_config is not None,
        "has_area_runtime": data.area_runtime is not None,
        "has_config_dict": isinstance(data.config, dict),
        "has_entities_dict": isinstance(data.entities, dict),
        "has_magic_entities_dict": isinstance(data.magic_entities, dict),
        "has_enabled_features_set": isinstance(data.enabled_features, set),
        "has_feature_configs_dict": isinstance(data.feature_configs, dict),
        "has_presence_sensors_list": isinstance(data.presence_sensors, list),
        "has_active_areas_list": isinstance(data.active_areas, list),
        "has_updated_at": data.updated_at is not None,
    }

    assert field_validation == snapshot


@pytest.mark.asyncio
async def test_coordinator_presence_configuration(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test presence sensor configuration in coordinator snapshot.

    Validates that presence sensors are properly configured with
    correct device classes and platform selection.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Snapshot presence configuration
    presence_config = {
        "presence_sensor_count": len(data.presence_sensors),
        "presence_sensors": sorted(data.presence_sensors),
        "device_classes": sorted(
            _string_config_list(data, CONF_PRESENCE_SENSOR_DEVICE_CLASS)
        ),
        "device_platforms": data.config.get(CONF_PRESENCE_DEVICE_PLATFORMS),
        "has_presence_sensors_in_snapshot": len(data.presence_sensors) > 0,
    }

    assert presence_config == snapshot


@pytest.mark.asyncio
async def test_coordinator_entity_grouping(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test entity grouping by domain in coordinator snapshot.

    Validates that entities are correctly grouped by domain and that
    magic (integration-generated) entities are properly tracked.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Snapshot entity grouping
    entity_grouping = {
        "regular_entity_domains": sorted(data.entities.keys()),
        "regular_entity_counts": {
            domain: len(entities) for domain, entities in data.entities.items()
        },
        "magic_entity_domains": sorted(data.magic_entities.keys()),
        "magic_entity_count_by_domain": {
            domain: len(entities) for domain, entities in data.magic_entities.items()
        },
    }

    assert entity_grouping == snapshot


@pytest.mark.asyncio
async def test_coordinator_feature_configuration(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test feature configuration structure in coordinator snapshot.

    Validates that feature enabling and configuration is properly
    captured in the coordinator data for each area.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Snapshot feature configuration
    feature_config = {
        "enabled_features": sorted(data.enabled_features),
        "feature_config_keys": sorted(data.feature_configs.keys()),
        "feature_configs": {
            key: data.feature_configs[key]
            for key in sorted(data.feature_configs.keys())
        },
        "feature_configs_count": len(data.feature_configs),
        "config_has_features_entry": CONF_ENABLED_FEATURES in data.config,
    }

    assert feature_config == snapshot


@pytest.mark.asyncio
async def test_coordinator_availability(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test coordinator availability status snapshot.

    Validates that coordinator refresh success is properly tracked
    and reflected in the area runtime data.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Snapshot availability
    availability = {
        "area_available": data.area_runtime.last_update_success,
        "coordinator_last_update_success": coordinator.last_update_success,
        "has_updated_at_timestamp": data.updated_at is not None,
    }

    assert availability == snapshot
