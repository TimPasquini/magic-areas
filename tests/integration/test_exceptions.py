"""Test exception handling in setup."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_BLE_TRACKER_ENTITIES,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.fixture(name="exception_config_entry")
def mock_config_entry_exception() -> MockConfigEntry:
    """Fixture for mock configuration entry with features enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {},
                MagicAreasFeatures.HEALTH: {},
                MagicAreasFeatures.WASP_IN_A_BOX: {},
                MagicAreasFeatures.BLE_TRACKER: {
                    CONF_BLE_TRACKER_ENTITIES: ["sensor.ble_tracker"],
                },
                MagicAreasFeatures.LIGHT_GROUPS: {},
                MagicAreasFeatures.MEDIA_PLAYER_GROUPS: {},
                MagicAreasFeatures.FAN_GROUPS: {},
                MagicAreasFeatures.CLIMATE_CONTROL: {},
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


async def test_binary_sensor_setup_exceptions(
    hass: HomeAssistant, exception_config_entry: MockConfigEntry
) -> None:
    """Test binary sensor setup exceptions."""
    # Patch the classes to raise exceptions
    with (
        patch(
            "custom_components.magic_areas.binary_sensor.aggregate_factory.AreaWaspInABoxBinarySensor",
            side_effect=RuntimeError("Wasp Error"),
        ),
        patch(
            "custom_components.magic_areas.binary_sensor.aggregate_factory.AreaBLETrackerBinarySensor",
            side_effect=RuntimeError("BLE Error"),
        ),
    ):
        await init_integration_helper(hass, [exception_config_entry])
        await hass.async_start()
        await hass.async_block_till_done()

        # Verify integration loaded despite errors
        assert exception_config_entry.state.name == "LOADED"

        await shutdown_integration(hass, [exception_config_entry])


async def test_switch_setup_exceptions(
    hass: HomeAssistant, exception_config_entry: MockConfigEntry
) -> None:
    """Test switch setup exceptions."""
    # Patch the classes to raise exceptions
    with (
        patch(
            "custom_components.magic_areas.switch.PresenceHoldSwitch",
            side_effect=Exception("Presence Hold Error"),
        ),
        patch(
            "custom_components.magic_areas.switch.LightControlSwitch",
            side_effect=Exception("Light Control Error"),
        ),
        patch(
            "custom_components.magic_areas.switch.MediaPlayerControlSwitch",
            side_effect=Exception("Media Player Control Error"),
        ),
        patch(
            "custom_components.magic_areas.switch.FanControlSwitch",
            side_effect=Exception("Fan Control Error"),
        ),
        patch(
            "custom_components.magic_areas.switch.ClimateControlSwitch",
            side_effect=Exception("Climate Control Error"),
        ),
    ):
        await init_integration_helper(hass, [exception_config_entry])
        await hass.async_start()
        await hass.async_block_till_done()

        # Verify integration loaded despite errors
        assert exception_config_entry.state.name == "LOADED"

        await shutdown_integration(hass, [exception_config_entry])
