"""Test initializing the system."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_RELOAD_ON_REGISTRY_CHANGE
from custom_components.magic_areas.core_constants import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)

_LOGGER = logging.getLogger(__name__)


async def test_init_default_config(
    hass: HomeAssistant, init_integration_fixture: MockConfigEntry
) -> None:
    """Test loading the integration."""

    # Validate the right entities were created.
    area_binary_sensor = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == STATE_OFF


async def test_migration_downgrade(
    hass: HomeAssistant,
) -> None:
    """Test that we do not migrate if version is newer than current."""

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN, data=data, version=3, minor_version=1  # Future version
    )
    mock_config_entry.add_to_hass(hass)

    from custom_components.magic_areas import async_migrate_entry

    assert await async_migrate_entry(hass, mock_config_entry) is False


async def test_reload_on_registry_change_disabled(
    hass: HomeAssistant,
) -> None:
    """Test that we do not reload if disabled in options."""

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_RELOAD_ON_REGISTRY_CHANGE] = False

    mock_config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    mock_config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    # Fire registry update event
    event_data = {
        "action": "create",
        "entity_id": "light.new_light",
    }
    hass.bus.async_fire(EVENT_ENTITY_REGISTRY_UPDATED, event_data)
    await hass.async_block_till_done()

    await shutdown_integration(hass, [mock_config_entry])
