"""Tests for the Magic Areas coordinator."""

from enum import Enum
from typing import Any

import pytest

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_registry

from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.coordinator import (
    MagicAreasCoordinator,
    MagicAreasData,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.ha_domains import BINARY_SENSOR_DOMAIN
from custom_components.magic_areas.models import MagicAreasConfigEntry
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_coordinator_builds_snapshot(
    hass: HomeAssistant, init_integration: MagicAreasConfigEntry
) -> None:
    """Test coordinator data mirrors area snapshot."""
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data
    # Verify snapshot is built correctly
    assert data.entities is not None
    assert data.magic_entities is not None
    assert data.presence_sensors is not None
    enabled_features = data.area_config.config.get(CONF_ENABLED_FEATURES, {})

    def _normalize_key(feature: object) -> str:
        if isinstance(feature, Enum):
            return str(feature.value)
        return str(feature)

    if isinstance(enabled_features, list):
        assert data.enabled_features == {
            _normalize_key(feature) for feature in enabled_features
        }
    elif isinstance(enabled_features, dict):
        assert data.enabled_features == {
            _normalize_key(feature) for feature in enabled_features
        }
        assert data.feature_configs == {
            _normalize_key(feature): values for feature, values in enabled_features.items()
        }


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_config_entry: MagicAreasConfigEntry
) -> None:
    """Test coordinator handles update failures."""
    from unittest.mock import patch

    area_config = AreaConfig(
        id="test_area",
        name="Test Area",
        slug="test_area",
        area_type="interior",
        config={CONF_ENABLED_FEATURES: {}},
        hass_config=mock_config_entry,
        icon=None,
        floor_id=None,
    )

    coordinator = MagicAreasCoordinator(hass, area_config, mock_config_entry)

    with patch(
        "custom_components.magic_areas.coordinator.load_area_entities",
        side_effect=RuntimeError("boom"),
    ), pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_refresh_updates_snapshot(
    hass: HomeAssistant, mock_config_entry: MagicAreasConfigEntry
) -> None:
    """Test coordinator refresh updates data snapshot."""
    from unittest.mock import patch

    area_config = AreaConfig(
        id="test_area",
        name="Test Area",
        slug="test_area",
        area_type="interior",
        config={
            CONF_ENABLED_FEATURES: {"test_feature": {"flag": True}},
            CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
        },
        hass_config=mock_config_entry,
        icon=None,
        floor_id=None,
    )

    async def _load_entities_impl(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Mock load_area_entities implementation."""
        return (
            {
                BINARY_SENSOR_DOMAIN: [
                    {
                        ATTR_ENTITY_ID: "binary_sensor.presence_one",
                        ATTR_DEVICE_CLASS: "motion",
                    }
                ],
                "sensor": [
                    {
                        "entity_id": "sensor.illuminance_one",
                        "device_class": "illuminance",
                        "unit_of_measurement": "lx",
                    }
                ]
            },
            {"sensor": [{"entity_id": "sensor.magic_one"}]}
        )

    coordinator = MagicAreasCoordinator(hass, area_config, mock_config_entry)

    with patch(
        "custom_components.magic_areas.coordinator.load_area_entities",
        side_effect=_load_entities_impl,
    ):
        await coordinator.async_refresh()
        assert coordinator.data is not None
        first_updated = coordinator.data.updated_at
        # After refresh, area entities should be updated with the mocked values
        assert coordinator.data.entities[BINARY_SENSOR_DOMAIN][0][ATTR_ENTITY_ID] == "binary_sensor.presence_one"
        assert coordinator.data.presence_sensors == ["binary_sensor.presence_one"]
        assert coordinator.data.enabled_features == {"test_feature"}
        assert coordinator.data.feature_configs == {"test_feature": {"flag": True}}

        async def _load_entities_second(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            """Mock second load_area_entities implementation."""
            return (
                {
                    BINARY_SENSOR_DOMAIN: [
                        {
                            ATTR_ENTITY_ID: "binary_sensor.presence_two",
                            ATTR_DEVICE_CLASS: "motion",
                        }
                    ]
                },
                {"sensor": [{"entity_id": "sensor.magic_one"}]}
            )

        with patch(
            "custom_components.magic_areas.coordinator.load_area_entities",
            side_effect=_load_entities_second,
        ):
            await coordinator.async_refresh()
            assert coordinator.data is not None
            assert coordinator.data.updated_at >= first_updated
            assert coordinator.data.presence_sensors == ["binary_sensor.presence_two"]


async def test_magic_area_include_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test including specific entities via config."""

    entity_registry = mock_registry(hass)

    # Create an entity NOT in the area
    external_entity = entity_registry.async_get_or_create(
        "switch", "test", "external_switch"
    )

    # Update config to include it
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [external_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify entity is loaded in coordinator snapshot
    assert coordinator.data is not None
    assert "switch" in coordinator.data.entities
    loaded_ids = [e["entity_id"] for e in coordinator.data.entities["switch"]]
    assert external_entity.entity_id in loaded_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_disabled(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that disabled entities are excluded from area entities."""
    entity_registry = mock_registry(hass)

    # Create a disabled entity
    disabled = entity_registry.async_get_or_create(
        "light",
        "test",
        "disabled_light",
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    # Create a normal entity
    normal = entity_registry.async_get_or_create("light", "test", "normal_light")

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [disabled.entity_id, normal.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify disabled entity is excluded
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert disabled.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_diagnostic(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that diagnostic entities are excluded from area entities."""
    entity_registry = mock_registry(hass)

    # Create a diagnostic entity
    diagnostic = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "diag_sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    # Create a normal entity
    normal = entity_registry.async_get_or_create("sensor", "test", "normal_sensor")

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [diagnostic.entity_id, normal.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify diagnostic entity is excluded
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert diagnostic.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_includes_normal_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that normal entities are included in area loading."""
    entity_registry = mock_registry(hass)

    # Create multiple normal entities
    light_entity = entity_registry.async_get_or_create(
        "light", "test", "test_light"
    )
    sensor_entity = entity_registry.async_get_or_create(
        "sensor", "test", "test_sensor"
    )
    switch_entity = entity_registry.async_get_or_create(
        "switch", "test", "test_switch"
    )

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [
        light_entity.entity_id,
        sensor_entity.entity_id,
        switch_entity.entity_id,
    ]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify all normal entities are included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert light_entity.entity_id in all_entity_ids
    assert sensor_entity.entity_id in all_entity_ids
    assert switch_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_excluded_entities_respected(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that excluded entities are not loaded."""
    entity_registry = mock_registry(hass)

    # Create entities
    excluded_entity = entity_registry.async_get_or_create(
        "light", "test", "excluded_light"
    )
    included_entity = entity_registry.async_get_or_create(
        "light", "test", "included_light"
    )

    # Update area config with excluded entities
    data = dict(mock_config_entry.data)
    data[CONF_EXCLUDE_ENTITIES] = [excluded_entity.entity_id]
    data[CONF_INCLUDE_ENTITIES] = [
        excluded_entity.entity_id,
        included_entity.entity_id,
    ]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify excluded entity is excluded even if explicitly included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert excluded_entity.entity_id not in all_entity_ids
    assert included_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_coordinator_entity_loading(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that coordinator correctly loads entities into snapshot."""
    entity_registry = mock_registry(hass)

    # Create entities with various states
    light1 = entity_registry.async_get_or_create("light", "test", "light1")
    light2 = entity_registry.async_get_or_create("light", "test", "light2")
    sensor1 = entity_registry.async_get_or_create("sensor", "test", "sensor1")

    # Update config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [
        light1.entity_id,
        light2.entity_id,
        sensor1.entity_id,
    ]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify coordinator snapshot has the entities
    assert coordinator.data is not None
    assert "light" in coordinator.data.entities
    assert "sensor" in coordinator.data.entities

    light_entities = coordinator.data.entities["light"]
    sensor_entities = coordinator.data.entities["sensor"]

    light_ids = [e.get("entity_id") for e in light_entities]
    sensor_ids = [e.get("entity_id") for e in sensor_entities]

    assert light1.entity_id in light_ids
    assert light2.entity_id in light_ids
    assert sensor1.entity_id in sensor_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_loads_device_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that coordinator loads entities linked to devices in area."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Setup area first
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_id = entry.runtime_data.coordinator._area_config.id

    # Create a device in the area
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("test", "test_device_1")},
    )
    device_registry.async_update_device(device.id, area_id=area_id)

    # Create an entity linked to the device (without area_id, linked via device)
    entity = entity_registry.async_get_or_create(
        "light",
        "test",
        "device_light",
        device_id=device.id,
    )

    # Wait for registry updates
    await hass.async_block_till_done()

    # Refresh coordinator to pick up device entities
    assert entry is not None
    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Verify device entity was loaded
    assert coordinator.data is not None
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_respects_config_entry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that entities from our own config entry are not included."""
    entity_registry = er.async_get(hass)

    # Create an entity that belongs to magic_areas config entry
    our_entity = entity_registry.async_get_or_create(
        "binary_sensor",
        "magic_areas",
        "our_area_state",
        config_entry=mock_config_entry,
    )

    # Create a normal entity not from our config
    normal_entity = entity_registry.async_get_or_create(
        "light", "test", "other_light"
    )

    # Update config to include both
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [our_entity.entity_id, normal_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify our entity is excluded even if included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    # Our config entry entity should be excluded
    assert our_entity.entity_id not in all_entity_ids
    # Normal entity should be included
    assert normal_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_available_platforms(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test available platforms from coordinator snapshot."""
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
    """Test that ConfigEntry updates are reflected in coordinator."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    # Verify initial state
    assert mock_config_entry.data[CONF_INCLUDE_ENTITIES] == []

    # Update via HA API
    new_data = dict(mock_config_entry.data)
    new_data[CONF_INCLUDE_ENTITIES] = ["light.new_light"]

    hass.config_entries.async_update_entry(mock_config_entry, data=new_data)
    await hass.async_block_till_done()

    # Verify update reflected in entry
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    assert entry.data[CONF_INCLUDE_ENTITIES] == ["light.new_light"]

    await shutdown_integration(hass, [mock_config_entry])
