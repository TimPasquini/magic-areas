"""Tests for the Magic Areas coordinator."""

from enum import Enum
from typing import Any

import pytest

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.coordinator import (
    MagicAreasCoordinator,
    MagicAreasData,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.ha_domains import BINARY_SENSOR_DOMAIN
from custom_components.magic_areas.models import MagicAreasConfigEntry


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
