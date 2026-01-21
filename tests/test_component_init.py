"""Tests for component setup helpers."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import EventBus, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas import async_setup_entry
from custom_components.magic_areas.config_keys import CONF_RELOAD_ON_REGISTRY_CHANGE
from custom_components.magic_areas.core_constants import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import get_basic_config_entry_data


async def test_async_setup_entry_reload_skipped_before_start(
    hass: HomeAssistant,
) -> None:
    """Test reload callback skips when Home Assistant is not running."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    magic_area = MagicMock()
    magic_area.name = data[ATTR_NAME]
    magic_area.id = data[ATTR_ID]
    magic_area.config = {}
    magic_area.entities = {}
    magic_area.magic_entities = {}
    magic_area.is_meta.return_value = False
    magic_area.make_entity_registry_filter.return_value = None
    magic_area.make_device_registry_filter.return_value = None
    magic_area.available_platforms.return_value = []
    magic_area.initialize = AsyncMock()
    magic_area.load_entities = AsyncMock()
    magic_area.get_presence_sensors.return_value = []
    magic_area.has_feature.return_value = False

    callbacks: dict[str, object] = {}

    def _fake_listen(bus, event_type, callback, *args, **kwargs):
        callbacks["registry"] = callback
        return lambda: None

    def _fake_listen_once(bus, event_type, callback):
        callbacks["reload"] = callback
        return lambda: None

    with (
        patch(
            "custom_components.magic_areas.get_magic_area_for_config_entry",
            return_value=magic_area,
        ),
        patch.object(EventBus, "async_listen", autospec=True, side_effect=_fake_listen),
        patch.object(
            EventBus,
            "async_listen_once",
            autospec=True,
            side_effect=_fake_listen_once,
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert await async_setup_entry(hass, config_entry) is True
        with patch.object(
            HomeAssistant, "is_running", new_callable=PropertyMock, return_value=False
        ):
            await callbacks["reload"](MagicMock())

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

    magic_area = MagicMock()
    magic_area.name = data[ATTR_NAME]
    magic_area.id = data[ATTR_ID]
    magic_area.config = {}
    magic_area.entities = {}
    magic_area.magic_entities = {}
    magic_area.is_meta.return_value = False
    magic_area.make_entity_registry_filter.return_value = None
    magic_area.make_device_registry_filter.return_value = None
    magic_area.available_platforms.return_value = []
    magic_area.initialize = AsyncMock()
    magic_area.load_entities = AsyncMock()
    magic_area.get_presence_sensors.return_value = []
    magic_area.has_feature.return_value = False

    callbacks: dict[str, object] = {}

    def _fake_listen(bus, event_type, callback, *args, **kwargs):
        callbacks["registry"] = callback
        return lambda: None

    def _fake_listen_once(bus, event_type, callback):
        callbacks["reload"] = callback
        return lambda: None

    with (
        patch(
            "custom_components.magic_areas.get_magic_area_for_config_entry",
            return_value=magic_area,
        ),
        patch.object(EventBus, "async_listen", autospec=True, side_effect=_fake_listen),
        patch.object(
            EventBus,
            "async_listen_once",
            autospec=True,
            side_effect=_fake_listen_once,
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        assert await async_setup_entry(hass, config_entry) is True
        await callbacks["registry"](MagicMock())

    update_entry.assert_not_called()
