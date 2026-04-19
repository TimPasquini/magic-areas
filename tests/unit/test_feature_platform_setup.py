"""Tests for shared platform setup helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.features.dispatch import async_setup_feature_platform


@pytest.mark.asyncio
async def test_async_setup_feature_platform_skips_when_data_unavailable() -> None:
    """Should refresh once and skip when coordinator data stays unavailable."""
    coordinator = AsyncMock()
    coordinator.data = None

    async def _keep_data_none() -> None:
        coordinator.data = None

    coordinator.async_refresh.side_effect = _keep_data_none

    config_entry = MagicMock()
    config_entry.runtime_data = MagicMock(coordinator=coordinator)
    async_add_entities = MagicMock()

    await async_setup_feature_platform(
        hass=MagicMock(),
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain="light",
        logger=MagicMock(),
    )

    coordinator.async_refresh.assert_called_once()
    async_add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_feature_platform_adds_base_and_feature_entities() -> None:
    """Should add entities and cleanup stale entries using shared setup path."""
    area_config = MagicMock()
    coordinator = AsyncMock()
    data = MagicMock(
        area_config=area_config,
        magic_entities={"light": [MagicMock()]},
    )
    coordinator.data = data
    config_entry = MagicMock()
    config_entry.runtime_data = MagicMock(coordinator=coordinator)
    async_add_entities = MagicMock()
    registry = MagicMock()
    hass = MagicMock()

    base_entity = MagicMock(spec=Entity)
    feature_entity = MagicMock(spec=Entity)

    with (
        patch(
            "custom_components.magic_areas.features.dispatch.collect_feature_entities",
            return_value=[feature_entity],
        ) as collect_entities,
        patch(
            "custom_components.magic_areas.features.registry.FEATURE_REGISTRY",
            registry,
            create=True,
        ),
        patch(
            "custom_components.magic_areas.helpers.cleanup_removed_entries"
        ) as cleanup_removed_entries,
    ):
        await async_setup_feature_platform(
            hass=hass,
            config_entry=config_entry,
            async_add_entities=async_add_entities,
            domain="light",
            logger=MagicMock(),
            base_entities_builder=lambda _a, _c, _d: [base_entity],
        )

    collect_entities.assert_called_once()
    assert collect_entities.call_args.kwargs["registry"] is registry

    async_add_entities.assert_called_once()
    added_entities = async_add_entities.call_args.args[0]
    assert added_entities == [base_entity, feature_entity]

    cleanup_removed_entries.assert_called_once_with(
        hass,
        added_entities,
        data.magic_entities["light"],
    )
