"""Unit tests for threshold aggregate entity resolution paths."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor.const import SensorDeviceClass

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
from custom_components.magic_areas.core.thresholds import get_illuminance_threshold_spec
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


def _make_data() -> SimpleNamespace:
    return SimpleNamespace(
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
        entity_references=SimpleNamespace(
            aggregates_by_device_class={
                SensorDeviceClass.ILLUMINANCE: "sensor.snapshot_fallback_illuminance"
            }
        ),
    )


@pytest.mark.parametrize(
    ("resolved", "expected"),
    [
        ("sensor.registry_illuminance", "sensor.registry_illuminance"),
        (None, "sensor.snapshot_fallback_illuminance"),
    ],
)
def test_threshold_resolution_prefers_registry_then_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    resolved: str | None,
    expected: str,
) -> None:
    """Threshold lookup should use aggregate runtime first, then snapshot refs."""
    resolver = MagicMock(return_value=resolved)
    monkeypatch.setattr(
        "custom_components.magic_areas.core.thresholds.resolve_aggregate_entity_id",
        resolver,
    )
    spec = get_illuminance_threshold_spec(
        MagicMock(),
        cast(MagicAreasData, _make_data()),
        _make_area_config(),
    )

    assert spec is not None
    assert spec[0] == expected


def test_threshold_resolution_returns_none_when_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Threshold lookup should skip creation when no aggregate target can be resolved."""
    data = _make_data()
    data.entity_references.aggregates_by_device_class = {}
    monkeypatch.setattr(
        "custom_components.magic_areas.core.thresholds.resolve_aggregate_entity_id",
        MagicMock(return_value=None),
    )

    spec = get_illuminance_threshold_spec(
        MagicMock(),
        cast(MagicAreasData, data),
        _make_area_config(),
    )

    assert spec is None
