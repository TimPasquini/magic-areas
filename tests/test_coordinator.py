"""Tests for the Magic Areas coordinator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.coordinator import (
    MagicAreasCoordinator,
    MagicAreasData,
)
from enum import Enum

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.ha_domains import BINARY_SENSOR_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.magic_areas.models import MagicAreasConfigEntry


async def test_coordinator_builds_snapshot(
    hass: HomeAssistant, init_integration: MagicAreasConfigEntry
) -> None:
    """Test coordinator data mirrors area snapshot."""
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data
    assert data.area == entry.runtime_data.area
    assert data.entities == entry.runtime_data.area.entities
    assert data.magic_entities == entry.runtime_data.area.magic_entities
    assert data.presence_sensors == entry.runtime_data.area.get_presence_sensors()
    enabled_features = entry.runtime_data.area.config.get(CONF_ENABLED_FEATURES, {})

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
    area = MagicMock()
    area.load_entities = AsyncMock(side_effect=RuntimeError("boom"))
    area.entities = {}
    area.magic_entities = {}
    area.config = {CONF_ENABLED_FEATURES: {}}
    area.get_presence_sensors.return_value = []

    coordinator = MagicAreasCoordinator(hass, area, mock_config_entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_refresh_updates_snapshot(
    hass: HomeAssistant, mock_config_entry: MagicAreasConfigEntry
) -> None:
    """Test coordinator refresh updates data snapshot."""
    area = MagicMock()
    area.entities = {}
    area.magic_entities = {}
    area.config = {
        CONF_ENABLED_FEATURES: {"test_feature": {"flag": True}},
        CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
    }

    async def _load_entities() -> None:
        area.entities = {
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
        }
        area.magic_entities = {"sensor": [{"entity_id": "sensor.magic_one"}]}

    area.load_entities = AsyncMock(side_effect=_load_entities)

    coordinator = MagicAreasCoordinator(hass, area, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.data is not None
    first_updated = coordinator.data.updated_at
    assert coordinator.data.entities == area.entities
    assert coordinator.data.magic_entities == area.magic_entities
    assert coordinator.data.presence_sensors == ["binary_sensor.presence_one"]
    assert coordinator.data.enabled_features == {"test_feature"}
    assert coordinator.data.feature_configs == {"test_feature": {"flag": True}}

    async def _load_entities_second() -> None:
        area.entities = {
            BINARY_SENSOR_DOMAIN: [
                {
                    ATTR_ENTITY_ID: "binary_sensor.presence_two",
                    ATTR_DEVICE_CLASS: "motion",
                }
            ]
        }
        area.magic_entities = {"sensor": [{"entity_id": "sensor.magic_one"}]}

    area.load_entities = AsyncMock(side_effect=_load_entities_second)
    await coordinator.async_refresh()
    assert coordinator.data is not None
    assert coordinator.data.updated_at >= first_updated
    if coordinator.data.presence_sensors != ["binary_sensor.presence_two"]:
        raise AssertionError(
            "presence_sensors mismatch; "
            f"presence_sensors={coordinator.data.presence_sensors}; "
            f"entities={area.entities}; "
            f"config={area.config}"
        )
