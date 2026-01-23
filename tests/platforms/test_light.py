"""Test for light groups."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.enums import (
    AreaStates,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
)
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_in_attribute,
    assert_state,
    get_basic_config_entry_data,
    shutdown_integration,
    wait_for_state,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.mocks import MockBinarySensor, MockLight

_LOGGER = logging.getLogger(__name__)


# Fixtures


@pytest.fixture(name="light_groups_config_entry")
def mock_config_entry_light_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.mock_light_1"],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE],
                    CONF_OVERHEAD_LIGHTS_STATES: [AreaStates.OCCUPIED],
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_light_groups")
async def setup_integration_light_groups(
    hass: HomeAssistant,
    light_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with BLE tracker config."""

    await init_integration_helper(hass, [light_groups_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [light_groups_config_entry])


# Tests


async def test_light_group_basic(
    hass: HomeAssistant,
    entities_light_one: list[MockLight],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_light_groups,
) -> None:
    """Test light group."""

    mock_light_entity_id = entities_light_one[0].entity_id
    mock_motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    light_group_entity_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    light_control_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"

    # Test mock entity created
    mock_light_state = hass.states.get(mock_light_entity_id)
    assert_state(mock_light_state, STATE_OFF)

    # Test light group created
    light_group_state = hass.states.get(light_group_entity_id)
    assert_state(light_group_state, STATE_OFF)
    assert_in_attribute(light_group_state, ATTR_ENTITY_ID, mock_light_entity_id)

    # Test light control switch created
    light_control_state = hass.states.get(light_control_entity_id)
    assert_state(light_control_state, STATE_OFF)

    # Test motion sensor created
    motion_sensor_state = hass.states.get(mock_motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_OFF)

    # Test area state
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)

    # Turn on light control
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: light_control_entity_id}
    )
    await hass.async_block_till_done()

    # Test light control switch state turned on
    light_control_state = hass.states.get(light_control_entity_id)
    assert_state(light_control_state, STATE_ON)

    # Turn motion sensor on
    entities_binary_sensor_motion_one[0].turn_on()
    await hass.async_block_till_done()

    motion_sensor_state = hass.states.get(mock_motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_ON)

    # Test area state is STATE_ON
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)

    # Check light group is on
    await wait_for_state(hass, light_group_entity_id, STATE_ON)

    # Turn motion sensor off
    entities_binary_sensor_motion_one[0].turn_off()
    await hass.async_block_till_done()

    # Test area state is STATE_OFF
    await wait_for_state(hass, area_sensor_entity_id, STATE_OFF)

    # Check light group is off
    await wait_for_state(hass, light_group_entity_id, STATE_OFF)
