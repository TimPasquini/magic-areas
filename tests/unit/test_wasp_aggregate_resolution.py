"""Unit tests for Wasp aggregate target resolution behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import STATE_OFF
from homeassistant.core import State
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import WASP_IN_A_BOX_BOX_DEVICE_CLASSES


def _make_area_config() -> AreaConfig:
    return AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=MagicMock(),
    )


def _make_coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = SimpleNamespace(
        feature_configs={
            MagicAreasFeatures.WASP_IN_A_BOX: {
                CONF_WASP_IN_A_BOX_DELAY: 0,
                CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 0,
                CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES: ["motion"],
            }
        },
        group_registry=GroupRegistry(),
    )
    return coordinator


def _set_hass_state_map(entity_ids: set[str]) -> MagicMock:
    hass = MagicMock()
    state_map = {entity_id: State(entity_id, STATE_OFF) for entity_id in entity_ids}
    hass.states.get.side_effect = lambda entity_id: state_map.get(entity_id)
    hass.loop.call_later = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_wasp_uses_registry_aggregate_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wasp sensor should load targets from aggregate runtime resolver when available."""
    coordinator = _make_coordinator()
    sensor = AreaWaspInABoxBinarySensor(_make_area_config(), coordinator)

    resolver_map = {"motion": "binary_sensor.registry_motion"}
    resolver_map.update(
        {
            str(device_class): f"binary_sensor.registry_{device_class}"
            for device_class in WASP_IN_A_BOX_BOX_DEVICE_CLASSES
        }
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.resolve_aggregate_entity_id",
        MagicMock(
            side_effect=lambda _hass, **kwargs: resolver_map.get(kwargs["device_class"])
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.async_track_state_change_event",
        lambda *args, **kwargs: (lambda: None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.AreaWaspInABoxBinarySensor.restore_state",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        RestoreEntity,
        "async_added_to_hass",
        AsyncMock(return_value=None),
    )

    sensor.hass = _set_hass_state_map(set(resolver_map.values()))
    await sensor.async_added_to_hass()

    assert sensor._wasp_sensors == ["binary_sensor.registry_motion"]
    assert set(sensor._box_sensors) == {
        f"binary_sensor.registry_{device_class}"
        for device_class in WASP_IN_A_BOX_BOX_DEVICE_CLASSES
    }


@pytest.mark.asyncio
async def test_wasp_skips_targets_when_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wasp sensor should keep sensor lists empty when no aggregate targets resolve."""
    coordinator = _make_coordinator()

    sensor = AreaWaspInABoxBinarySensor(_make_area_config(), coordinator)
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.resolve_aggregate_entity_id",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.async_track_state_change_event",
        lambda *args, **kwargs: (lambda: None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.binary_sensor.wasp_in_a_box.AreaWaspInABoxBinarySensor.restore_state",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        RestoreEntity,
        "async_added_to_hass",
        AsyncMock(return_value=None),
    )

    sensor.hass = _set_hass_state_map(set())
    await sensor.async_added_to_hass()

    assert sensor._wasp_sensors == []
    assert sensor._box_sensors == []
