"""Unit tests for threshold aggregate entity resolution paths."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor.const import SensorDeviceClass

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.runtime_model import AreaConfig, AreaRuntime
from custom_components.magic_areas.core.runtime_model.references import EntityReferences
from custom_components.magic_areas.core.aggregates.runtime import (
    get_illuminance_threshold_spec,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


def _make_area_config() -> AreaConfig:
    return AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=MagicMock(),
    )


def _make_data() -> MagicAreasData:
    area_config = _make_area_config()
    return MagicAreasData(
        enabled_features={MagicAreasFeatures.AGGREGATES},
        feature_configs={
            MagicAreasFeatures.AGGREGATES: {
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 75,
                CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [
                    SensorDeviceClass.ILLUMINANCE,
                ],
            }
        },
        entities={
            "sensor": [
                {
                    "device_class": SensorDeviceClass.ILLUMINANCE,
                    "entity_id": "sensor.lux_a",
                }
            ]
        },
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        group_registry=GroupRegistry(),
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=AreaRuntime(),
        updated_at=datetime.now(),
    )


def test_threshold_resolution_uses_registry_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Threshold lookup should use aggregate runtime resolver target."""
    monkeypatch.setattr(
        "custom_components.magic_areas.core.aggregates.runtime.resolve_aggregate_entity_id",
        MagicMock(return_value="sensor.registry_illuminance"),
    )
    spec = get_illuminance_threshold_spec(
        MagicMock(),
        _make_data(),
        _make_area_config(),
    )

    assert spec is not None
    assert spec[0] == "sensor.registry_illuminance"


def test_threshold_resolution_returns_none_when_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Threshold lookup should skip creation when no aggregate target can be resolved."""
    monkeypatch.setattr(
        "custom_components.magic_areas.core.aggregates.runtime.resolve_aggregate_entity_id",
        MagicMock(return_value=None),
    )

    spec = get_illuminance_threshold_spec(
        MagicMock(),
        _make_data(),
        _make_area_config(),
    )

    assert spec is None
