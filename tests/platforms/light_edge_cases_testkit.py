"""Shared fixtures for light edge-case platform tests."""

import pytest
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from typing import cast

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LightGroupRuntimeController,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.entities import setup_mock_entities
from tests.mocks import MockLight


def get_light_group_runtime(
    config_entry: MockConfigEntry,
    category: str = CONF_OVERHEAD_LIGHTS,
) -> LightGroupRuntimeController:
    """Return a non-entity light-group runtime controller from a config entry."""
    controllers = config_entry.runtime_data.runtime_controllers or []
    for controller in controllers:
        if getattr(controller, "category", None) == category:
            return cast(LightGroupRuntimeController, controller)
    raise AssertionError(f"{category} runtime controller not found")


@pytest.fixture(name="light_edge_cases_config_entry")
def mock_config_entry_light_edge_cases() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1", "light.overhead_2"],
                    CONF_OVERHEAD_LIGHTS_STATES: [
                        AreaStates.OCCUPIED,
                        AreaStates.BRIGHT,
                    ],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="light_edge_cases_config_entry_limited")
def mock_config_entry_light_edge_cases_limited() -> MockConfigEntry:
    """Fixture for mock configuration entry with limited features/states."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1"],
                    CONF_OVERHEAD_LIGHTS_STATES: [AreaStates.OCCUPIED],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [],
                },
            },
            CONF_SECONDARY_STATES: {CONF_DARK_ENTITY: "binary_sensor.dark_sensor"},
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="entities_light_edge_cases")
async def setup_entities_light_edge_cases(hass: HomeAssistant) -> list[MockLight]:
    """Create mock lights."""
    lights = [
        MockLight("overhead_1", "off", unique_id="overhead_1"),
        MockLight("overhead_2", "off", unique_id="overhead_2"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    return lights
