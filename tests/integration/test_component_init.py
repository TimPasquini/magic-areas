"""Tests for component setup helpers."""

from collections.abc import Awaitable, Callable
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import EventBus, HomeAssistant
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas import (
    async_setup_entry,
    async_unload_entry,
    async_update_options,
)
from custom_components.magic_areas.components import MagicAreasRuntimeData
from custom_components.magic_areas.config_keys.area import CONF_RELOAD_ON_REGISTRY_CHANGE
from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data

EventCallback = Callable[[object], Awaitable[object]]


async def test_async_update_options_reloads_config_entry(
    hass: HomeAssistant,
) -> None:
    """The registered options listener should reload its config entry."""
    config_entry = MockConfigEntry(domain=DOMAIN)

    with patch.object(
        hass.config_entries,
        "async_reload",
        new=AsyncMock(return_value=True),
    ) as async_reload:
        await async_update_options(
            hass,
            cast(ConfigEntry[MagicAreasRuntimeData], config_entry),
        )

    async_reload.assert_awaited_once_with(config_entry.entry_id)


async def test_async_unload_entry_cleans_runtime_resources(
    hass: HomeAssistant,
) -> None:
    """The HA unload entry point should unload platforms and runtime resources."""
    config_entry = MockConfigEntry(domain=DOMAIN)
    listener = MagicMock()
    coordinator = MagicMock()
    coordinator.data.area_config.available_platforms.return_value = [
        "binary_sensor",
        "switch",
    ]
    coordinator.async_shutdown = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        coordinator=coordinator,
        listeners=[listener],
    )

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=True),
    ) as async_unload_platforms:
        assert await async_unload_entry(
            hass,
            cast(ConfigEntry[MagicAreasRuntimeData], config_entry),
        )

    async_unload_platforms.assert_awaited_once_with(
        config_entry,
        ["binary_sensor", "switch"],
    )
    coordinator.async_shutdown.assert_awaited_once_with()
    listener.assert_called_once_with()


async def test_async_setup_entry_reload_skipped_before_start(
    hass: HomeAssistant,
) -> None:
    """Test reload callback skips when Home Assistant is not running."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    callbacks: dict[str, EventCallback] = {}

    def _fake_listen(
        bus: object,
        event_type: object,
        callback: EventCallback,
        *args: object,
        **kwargs: object,
    ) -> Callable[[], None]:
        callbacks[str(event_type)] = callback
        return lambda: None

    with (
        patch(
            "custom_components.magic_areas.build_area_config_for_config_entry",
            return_value=MagicMock(is_meta=MagicMock(return_value=False)),
        ),
        patch.object(EventBus, "async_listen", autospec=True, side_effect=_fake_listen),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert await async_setup_entry(
            hass, cast(ConfigEntry[MagicAreasRuntimeData], config_entry)
        ) is True
        with patch.object(
            HomeAssistant, "is_running", new_callable=PropertyMock, return_value=False
        ):
            await callbacks[str(EVENT_ENTITY_REGISTRY_UPDATED)](MagicMock())

    update_entry.assert_not_called()


async def test_async_setup_entry_registry_update_respects_disabled_reload(
    hass: HomeAssistant,
) -> None:
    """Test registry update does not reload when disabled in options."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options={CONF_RELOAD_ON_REGISTRY_CHANGE: False},
    )
    config_entry.add_to_hass(hass)

    callbacks: dict[str, EventCallback] = {}

    def _fake_listen(
        bus: object,
        event_type: object,
        callback: EventCallback,
        *args: object,
        **kwargs: object,
    ) -> Callable[[], None]:
        callbacks[str(event_type)] = callback
        return lambda: None

    with (
        patch(
            "custom_components.magic_areas.build_area_config_for_config_entry",
            return_value=MagicMock(is_meta=MagicMock(return_value=False)),
        ),
        patch.object(EventBus, "async_listen", autospec=True, side_effect=_fake_listen),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert await async_setup_entry(
            hass, cast(ConfigEntry[MagicAreasRuntimeData], config_entry)
        ) is True
        await callbacks[str(EVENT_ENTITY_REGISTRY_UPDATED)](MagicMock())

    update_entry.assert_not_called()
