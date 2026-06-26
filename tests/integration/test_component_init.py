"""Tests for component setup helpers."""

from collections.abc import Awaitable, Callable
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import EventBus, HomeAssistant
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas import async_setup_entry
from custom_components.magic_areas.components import MagicAreasRuntimeData
from custom_components.magic_areas.config_keys.area import (
    CONF_RELOAD_ON_REGISTRY_CHANGE,
)
from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data

EventCallback = Callable[[object], Awaitable[object]]


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
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert (
            await async_setup_entry(
                hass, cast(ConfigEntry[MagicAreasRuntimeData], config_entry)
            )
            is True
        )
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
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert (
            await async_setup_entry(
                hass, cast(ConfigEntry[MagicAreasRuntimeData], config_entry)
            )
            is True
        )
        await callbacks[str(EVENT_ENTITY_REGISTRY_UPDATED)](MagicMock())

    update_entry.assert_not_called()
