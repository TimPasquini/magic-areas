"""Shared fixtures/helpers for Wasp-in-a-Box platform tests."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor


@pytest.fixture(name="wasp_in_a_box_config_entry")
def mock_config_entry_wasp_in_a_box() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.WASP_IN_A_BOX: {
                    CONF_WASP_IN_A_BOX_DELAY: 0,
                    CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 1,
                },
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1},
            },
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_wasp_in_a_box")
async def setup_integration_wasp_in_a_box(
    hass: HomeAssistant,
    wasp_in_a_box_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with Wasp in a box (and aggregates) config."""
    await init_integration_helper(hass, [wasp_in_a_box_config_entry])
    yield
    await shutdown_integration(hass, [wasp_in_a_box_config_entry])


@pytest.fixture(name="entities_wasp_in_a_box")
async def setup_entities_wasp_in_a_box(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create motion and door sensors."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion_sensor",
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        ),
        MockBinarySensor(
            name="door_sensor",
            unique_id="unique_door",
            device_class=BinarySensorDeviceClass.DOOR,
        ),
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities
