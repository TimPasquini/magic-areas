"""Coordinator lifecycle and snapshot event contract tests."""

from datetime import UTC, datetime
from enum import Enum
from typing import cast
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.components import (
    BINARY_SENSOR_DOMAIN,
    MagicAreasRuntimeData,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.coordinator import MagicAreasCoordinator, MagicAreasData
from custom_components.magic_areas.core.runtime_model import AreaConfig, AreaRuntime
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.runtime_model import EntityReferences
from custom_components.magic_areas.enums import MagicAreasEvents


def _build_area_config(
    *,
    area_id: str,
    area_type: str = "interior",
    config: dict[str, object] | None = None,
    hass_config: ConfigEntry[MagicAreasRuntimeData],
    floor_id: str | None = None,
) -> AreaConfig:
    """Create area config for coordinator lifecycle tests."""
    area_name = area_id.replace("_", " ").title()
    return AreaConfig(
        id=area_id,
        name=area_name,
        slug=area_id,
        area_type=area_type,
        config=config or {CONF_ENABLED_FEATURES: {}},
        hass_config=hass_config,
        icon=None,
        floor_id=floor_id,
    )


def _build_snapshot(area_config: AreaConfig, *, child_areas: list[str] | None = None) -> MagicAreasData:
    """Create a minimal snapshot for coordinator tests."""
    return MagicAreasData(
        entities={},
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        child_areas=child_areas or [],
        config={},
        enabled_features=set(),
        feature_configs={},
        group_registry=GroupRegistry(),
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=AreaRuntime(),
        updated_at=datetime.now(UTC),
    )


async def test_coordinator_builds_snapshot(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Coordinator data mirrors normalized area snapshot contents."""
    entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data
    assert data.entities is not None
    assert data.magic_entities is not None
    assert data.presence_sensors is not None
    enabled_features = data.area_config.config.get(CONF_ENABLED_FEATURES, {})

    def _normalize_key(feature: object) -> str:
        if isinstance(feature, Enum):
            return str(feature.value)
        return str(feature)

    if isinstance(enabled_features, list):
        assert data.enabled_features == {_normalize_key(feature) for feature in enabled_features}
    elif isinstance(enabled_features, dict):
        assert data.enabled_features == {_normalize_key(feature) for feature in enabled_features}
        assert data.feature_configs == {
            _normalize_key(feature): values
            for feature, values in enabled_features.items()
        }


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator update wraps runtime failures with UpdateFailed."""
    area_config = _build_area_config(
        area_id="test_area",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))

    with patch(
        "custom_components.magic_areas.coordinator.pipeline.snapshot.load_area_entities",
        side_effect=RuntimeError("boom"),
    ), pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_refresh_updates_snapshot(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator refresh replaces snapshot and updates presence sensors."""
    area_config = _build_area_config(
        area_id="test_area",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
        config={
            CONF_ENABLED_FEATURES: {"test_feature": {"flag": True}},
            CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
        },
    )

    async def _load_entities_first(*args: object, **kwargs: object) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
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
                ],
            },
            {"sensor": [{"entity_id": "sensor.magic_one"}]},
        )

    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))

    with patch(
        "custom_components.magic_areas.coordinator.pipeline.snapshot.load_area_entities",
        side_effect=_load_entities_first,
    ):
        await coordinator.async_refresh()
        assert coordinator.data is not None
        first_updated = coordinator.data.updated_at
        assert (
            coordinator.data.entities[BINARY_SENSOR_DOMAIN][0][ATTR_ENTITY_ID]
            == "binary_sensor.presence_one"
        )
        assert coordinator.data.presence_sensors == ["binary_sensor.presence_one"]
        assert coordinator.data.enabled_features == {"test_feature"}
        assert coordinator.data.feature_configs == {"test_feature": {"flag": True}}

        async def _load_entities_second(
            *args: object, **kwargs: object
        ) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
            return (
                {
                    BINARY_SENSOR_DOMAIN: [
                        {
                            ATTR_ENTITY_ID: "binary_sensor.presence_two",
                            ATTR_DEVICE_CLASS: "motion",
                        }
                    ]
                },
                {"sensor": [{"entity_id": "sensor.magic_one"}]},
            )

        with patch(
            "custom_components.magic_areas.coordinator.pipeline.snapshot.load_area_entities",
            side_effect=_load_entities_second,
        ):
            await coordinator.async_refresh()
            assert coordinator.data is not None
            assert coordinator.data.updated_at >= first_updated
            assert coordinator.data.presence_sensors == ["binary_sensor.presence_two"]


async def test_regular_coordinator_dispatches_snapshot_ready_signal(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Regular-area refresh emits AREA_SNAPSHOT_READY event."""
    area_config = _build_area_config(
        area_id="kitchen",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))
    snapshot = _build_snapshot(area_config)

    with (
        patch("custom_components.magic_areas.coordinator.build_snapshot", return_value=snapshot),
        patch("custom_components.magic_areas.coordinator.dispatcher_send") as mock_send,
    ):
        await coordinator.async_refresh()
        assert coordinator.data is snapshot

    mock_send.assert_called_once_with(
        hass,
        MagicAreasEvents.AREA_SNAPSHOT_READY,
        "interior",
        None,
        "kitchen",
        snapshot.updated_at.isoformat(),
    )


async def test_meta_coordinator_retries_snapshot_ready_after_startup(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Meta coordinator retains startup snapshot-ready triggers until ready."""
    area_config = _build_area_config(
        area_id="global",
        area_type="meta",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))
    lifecycle = coordinator.lifecycle
    assert lifecycle is not None

    with patch.object(hass.config_entries, "async_schedule_reload"):
        lifecycle.handle_snapshot_ready("interior", None, "kitchen")
        await hass.async_block_till_done()
        assert lifecycle.reloading is False

        lifecycle.handle_started()
        await hass.async_block_till_done()
        assert lifecycle.pending_reload_handle is not None
        assert lifecycle.meta_data_retry_attempts >= 1

        coordinator.data = _build_snapshot(area_config, child_areas=["kitchen"])
        await lifecycle.async_retry_reload("interior", "kitchen")
        await lifecycle.async_execute_reload("interior", "kitchen")
        assert lifecycle.reloading is True


async def test_meta_coordinator_retries_until_meta_snapshot_available(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Meta reload retries until child mapping exists in snapshot."""
    area_config = _build_area_config(
        area_id="first_floor",
        area_type="meta",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
        floor_id="1",
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))
    lifecycle = coordinator.lifecycle
    assert lifecycle is not None

    with patch.object(hass.config_entries, "async_schedule_reload"):
        lifecycle.evaluate_and_schedule_reload("interior", "kitchen")
        assert lifecycle.pending_reload_handle is not None
        assert lifecycle.reloading is False

        coordinator.data = _build_snapshot(area_config, child_areas=["kitchen"])
        await lifecycle.async_retry_reload("interior", "kitchen")
        await lifecycle.async_execute_reload("interior", "kitchen")
        assert lifecycle.reloading is True


async def test_meta_coordinator_snapshot_ready_reloads_for_matching_child(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Meta coordinator schedules reload for matching child updates."""
    area_config = _build_area_config(
        area_id="interior",
        area_type="meta",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))
    coordinator.data = _build_snapshot(area_config, child_areas=["kitchen"])

    lifecycle = coordinator.lifecycle
    assert lifecycle is not None
    with patch.object(lifecycle, "schedule_reload_handle") as mock_schedule:
        lifecycle.evaluate_and_schedule_reload("interior", "kitchen")

    assert lifecycle.meta_data_retry_attempts == 0
    mock_schedule.assert_called_once()
    assert mock_schedule.call_args.kwargs["callback"] == lifecycle.async_execute_reload


async def test_meta_coordinator_snapshot_ready_ignores_unmatched_child(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Meta coordinator ignores unrelated snapshot-ready events."""
    area_config = _build_area_config(
        area_id="interior",
        area_type="meta",
        hass_config=cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry),
    )
    coordinator = MagicAreasCoordinator(hass, area_config, cast(ConfigEntry[MagicAreasRuntimeData], mock_config_entry))
    coordinator.data = _build_snapshot(area_config, child_areas=["kitchen"])

    lifecycle = coordinator.lifecycle
    assert lifecycle is not None
    with patch.object(lifecycle, "schedule_reload_handle") as mock_schedule:
        lifecycle.evaluate_and_schedule_reload("exterior", "garage")

    assert lifecycle.meta_data_retry_attempts == 0
    assert lifecycle.reloading is False
    mock_schedule.assert_not_called()
