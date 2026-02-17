"""Snapshot tests for Magic Areas coordinator.

Tests coordinator data snapshots including MagicAreasData structure,
entity grouping, presence sensors, and feature configurations.
"""


import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.coordinator import (
    MagicAreasData,
)


@pytest.mark.asyncio
async def test_coordinator_snapshot_structure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test MagicAreasData structure snapshot.

    Captures the complete structure of MagicAreasData including all
    fields and their types for validation and reference.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create a serializable snapshot of the data structure
    data_snapshot = {
        "area_id": data.area_config.slug,
        "area_name": data.area_config.name,
        "config_keys": sorted(data.config.keys()),
        "enabled_features": sorted(data.enabled_features),
        "feature_configs": {
            k: type(v).__name__ for k, v in data.feature_configs.items()
        },
        "presence_sensor_count": len(data.presence_sensors),
        "entity_domains": sorted(data.entities.keys()),
        "magic_entity_domains": sorted(data.magic_entities.keys()),
        "has_updated_at": hasattr(data, "updated_at"),
        "active_areas_type": type(data.active_areas).__name__,
    }

    # Snapshot the coordinator data structure
    assert data_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_snapshot_entities(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test entity grouping in coordinator snapshot.

    Captures how entities are grouped by domain and their structure
    within the coordinator data.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create entity domain summary
    entity_summary = {
        "domains": list(data.entities.keys()),
        "domain_entity_counts": {
            domain: len(entities) for domain, entities in data.entities.items()
        },
        "magic_domains": list(data.magic_entities.keys()),
        "magic_domain_entity_counts": {
            domain: len(entities) for domain, entities in data.magic_entities.items()
        },
    }

    # Snapshot entity grouping
    assert entity_summary == snapshot


@pytest.mark.asyncio
async def test_coordinator_snapshot_presence(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test presence sensors in coordinator snapshot.

    Captures the structure and configuration of presence sensors
    including device classes and entity references.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create presence sensor summary
    presence_summary = {
        "presence_sensor_count": len(data.presence_sensors),
        "presence_sensors": data.presence_sensors,
        "presence_device_platforms": data.config.get(
            CONF_PRESENCE_DEVICE_PLATFORMS, []
        ),
        "presence_device_classes": data.config.get(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS, []
        ),
    }

    # Snapshot presence configuration
    assert presence_summary == snapshot


@pytest.mark.asyncio
async def test_coordinator_snapshot_features(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test feature configs in coordinator snapshot.

    Captures the structure of enabled features and their configurations
    as stored in the coordinator data.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create feature summary
    feature_summary = {
        "enabled_features": sorted(data.enabled_features),
        "feature_config_keys": sorted(data.feature_configs.keys()),
        "has_feature_configs": len(data.feature_configs) > 0,
    }

    # Snapshot feature configuration
    assert feature_summary == snapshot


@pytest.mark.asyncio
async def test_coordinator_data_feature_structure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test coordinator snapshot feature data structure.

    Captures the structure of enabled features in coordinator data.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Create feature structure snapshot
    feature_snapshot = {
        "enabled_features_count": len(coordinator.data.enabled_features),
        "feature_configs_count": len(coordinator.data.feature_configs),
        "feature_names": sorted(coordinator.data.enabled_features),
    }

    # Snapshot feature structure
    assert feature_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_config_snapshot(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full config snapshot in coordinator.

    Captures the complete configuration stored in the coordinator
    including all area-specific settings.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Extract key configuration fields
    config_snapshot = {
        "area_id": data.config.get("id"),
        "area_type": data.config.get("type"),
        "presence_platforms": data.config.get(CONF_PRESENCE_DEVICE_PLATFORMS),
        "presence_device_classes": data.config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS),
        "enabled_features_keys": list(data.config.get(CONF_ENABLED_FEATURES, {}).keys()),
    }

    # Snapshot config state
    assert config_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_active_areas(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test active areas tracking in coordinator.

    Captures the structure of active areas tracking including
    area state resolution.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create active areas snapshot
    active_areas_snapshot = {
        "active_areas": data.active_areas,
        "active_areas_count": len(data.active_areas),
        "active_areas_type": type(data.active_areas).__name__,
    }

    # Snapshot active areas
    assert active_areas_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_metadata(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test coordinator metadata and timestamps.

    Captures metadata like update timestamps and last update success status.
    """
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data

    # Create metadata snapshot
    metadata_snapshot = {
        "has_updated_at": data.updated_at is not None,
        "area_id": data.area_config.slug,
        "area_last_update_success": data.area_runtime.last_update_success,
    }

    # Snapshot metadata
    assert metadata_snapshot == snapshot
