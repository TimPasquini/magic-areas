"""Snapshot tests for Magic Areas entity creation.

Tests entity creation results including light groups, binary sensors,
and aggregated sensors using snapshots to validate structure.
"""


import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion


@pytest.mark.asyncio
async def test_light_group_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test light group entity structure snapshot.

    Captures the structure of light entities including
    entity domains and organization.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Get light entities from coordinator
    light_entities = coordinator.data.entities.get(LIGHT_DOMAIN, [])

    # Create snapshot of light entities structure
    light_snapshot = {
        "light_entity_count": len(light_entities),
        "has_light_entities": len(light_entities) > 0,
    }

    # Also check for magic light group
    magic_lights = coordinator.data.magic_entities.get(LIGHT_DOMAIN, [])
    light_snapshot["magic_light_count"] = len(magic_lights)

    # Snapshot light group structure
    assert light_snapshot == snapshot


@pytest.mark.asyncio
async def test_binary_sensor_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test binary sensor entity structure snapshot.

    Captures the organization of binary sensor entities
    in the coordinator data.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    binary_sensors = coordinator.data.entities.get(BINARY_SENSOR_DOMAIN, [])

    # Create snapshot of binary sensors
    binary_sensor_snapshot = {
        "binary_sensor_count": len(binary_sensors),
        "has_binary_sensors": len(binary_sensors) > 0,
    }

    # Check for magic binary sensors
    magic_binary_sensors = coordinator.data.magic_entities.get(
        BINARY_SENSOR_DOMAIN, []
    )
    binary_sensor_snapshot["magic_binary_sensor_count"] = len(magic_binary_sensors)

    # Snapshot binary sensor structure
    assert binary_sensor_snapshot == snapshot


@pytest.mark.asyncio
async def test_sensor_entity_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test sensor entity structure snapshot.

    Captures the organization of sensor entities
    within the coordinator data.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Get sensor entities
    sensors = coordinator.data.entities.get(SENSOR_DOMAIN, [])

    # Create snapshot of sensors
    sensor_snapshot = {
        "sensor_count": len(sensors),
        "has_sensors": len(sensors) > 0,
    }

    # Check for magic sensors
    magic_sensors = coordinator.data.magic_entities.get(SENSOR_DOMAIN, [])
    sensor_snapshot["magic_sensor_count"] = len(magic_sensors)

    # Snapshot sensor structure
    assert sensor_snapshot == snapshot


@pytest.mark.asyncio
async def test_presence_sensor_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test presence sensor structure snapshot.

    Captures the structure of presence tracking sensors created
    by the Magic Areas integration.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Get presence sensors
    presence_sensors = coordinator.data.presence_sensors

    # Create snapshot of presence sensors
    presence_snapshot = {
        "presence_sensor_count": len(presence_sensors),
        "has_presence_sensors": len(presence_sensors) > 0,
        "presence_sensors": sorted(presence_sensors),
    }

    # Snapshot presence sensor structure
    assert presence_snapshot == snapshot


@pytest.mark.asyncio
async def test_magic_entity_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test magic entity structure snapshot.

    Captures the structure of magic entities created by the integration
    including their domains and organization.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Create snapshot of magic entities by domain
    magic_entities_snapshot = {
        "magic_domains": sorted(coordinator.data.magic_entities.keys()),
        "domain_entity_counts": {
            domain: len(entities)
            for domain, entities in coordinator.data.magic_entities.items()
        },
        "magic_entity_ids": {
            domain: sorted(entity["entity_id"] for entity in entities)
            for domain, entities in coordinator.data.magic_entities.items()
        },
        "total_magic_entities": sum(
            len(entities) for entities in coordinator.data.magic_entities.values()
        ),
    }

    # Snapshot magic entity structure
    assert magic_entities_snapshot == snapshot


@pytest.mark.asyncio
async def test_entity_domain_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test entity domain structure snapshot.

    Captures the overall organization of entities by domain
    including both regular and magic entities.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Create detailed entity snapshot
    entity_details = {
        "entity_domains": sorted(coordinator.data.entities.keys()),
        "domain_counts": {
            domain: len(entities)
            for domain, entities in coordinator.data.entities.items()
        },
        "entity_ids": {
            domain: sorted(entity["entity_id"] for entity in entities)
            for domain, entities in coordinator.data.entities.items()
        },
        "total_entities": sum(
            len(entities) for entities in coordinator.data.entities.values()
        ),
        "magic_domains": sorted(coordinator.data.magic_entities.keys()),
    }

    # Snapshot entity structure
    assert entity_details == snapshot


@pytest.mark.asyncio
async def test_magic_sensor_structure_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test magic sensor entity structure snapshot.

    Captures the organization of magic sensor entities
    within the coordinator data.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Create magic sensor structure snapshot
    magic_sensor_snapshot = {
        "magic_sensor_count": len(coordinator.data.magic_entities.get(SENSOR_DOMAIN, [])),
        "has_magic_sensors": len(coordinator.data.magic_entities.get(SENSOR_DOMAIN, [])) > 0,
        "sensor_count": len(coordinator.data.entities.get(SENSOR_DOMAIN, [])),
    }

    # Snapshot magic sensor structure
    assert magic_sensor_snapshot == snapshot


@pytest.mark.asyncio
async def test_coordinator_data_snapshot(
    hass: HomeAssistant,
    snapshot_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full coordinator data snapshot.

    Captures the complete structure of coordinator data
    including all entity information.
    """
    entry = snapshot_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None

    # Create comprehensive snapshot
    full_snapshot = {
        "area_id": coordinator.data.area_config.slug,
        "presence_sensor_count": len(coordinator.data.presence_sensors),
        "entity_domain_count": len(coordinator.data.entities),
        "magic_entity_domain_count": len(coordinator.data.magic_entities),
        "enabled_features_count": len(coordinator.data.enabled_features),
        "total_config_keys": len(coordinator.data.config),
    }

    # Snapshot full coordinator data
    assert full_snapshot == snapshot
