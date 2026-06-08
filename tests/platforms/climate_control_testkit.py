"""Shared fixtures for climate-control platform tests."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_AWAY,
    PRESET_NONE,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_ENABLED_FEATURES,
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
from tests.mocks import MockClimate


@pytest.fixture(name="climate_control_config_entry")
def mock_config_entry_climate_control() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.CLIMATE_CONTROL: {
                    CONF_CLIMATE_CONTROL_ENTITY_ID: f"{CLIMATE_DOMAIN}.mock_climate",
                    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: PRESET_NONE,
                    CONF_CLIMATE_CONTROL_PRESET_CLEAR: PRESET_AWAY,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_climate_control")
async def setup_integration_climate_control(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with climate-control config."""
    await init_integration_helper(hass, [climate_control_config_entry])
    yield
    await shutdown_integration(hass, [climate_control_config_entry])


@pytest.fixture(name="entities_climate_one")
async def setup_entities_climate_one(hass: HomeAssistant) -> list[MockClimate]:
    """Create one mock climate and set up the system with it."""
    mock_climate_entities = [
        MockClimate(
            name="mock_climate",
            unique_id="unique_mock_climate",
        )
    ]
    await setup_mock_entities(
        hass, CLIMATE_DOMAIN, {DEFAULT_MOCK_AREA: mock_climate_entities}
    )
    return mock_climate_entities
