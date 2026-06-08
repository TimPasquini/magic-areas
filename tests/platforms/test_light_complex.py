"""Test for complex light group behavior."""


import pytest
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.waits import wait_for_state
from tests.helpers_timing import create_area_state_change_event
from tests.helpers.entities import setup_mock_entities
from tests.helpers import (
    get_basic_config_entry_data,
    shutdown_integration,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.mocks import MockLight


@pytest.fixture(name="light_complex_config_entry")
def mock_config_entry_light_complex() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1"],
                    CONF_OVERHEAD_LIGHTS_STATES: [
                        AreaStates.OCCUPIED,
                        AreaStates.BRIGHT,
                    ],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="entities_light_complex")
async def setup_entities_light_complex(hass: HomeAssistant) -> list[MockLight]:
    """Create mock lights."""
    lights = [MockLight("overhead_1", STATE_OFF, unique_id="overhead_1")]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    return lights


async def test_light_group_state_change_logic(
    hass: HomeAssistant,
    light_complex_config_entry: MockConfigEntry,
    entities_light_complex: list[MockLight],
) -> None:
    """Test light group state change logic."""

    await init_integration_helper(hass, [light_complex_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    light_control_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )

    # Verify light group is set up correctly
    light_group_state = hass.states.get(light_group_id)
    assert light_group_state is not None
    assert "light.overhead_1" in light_group_state.attributes["entity_id"]

    # Initial state
    await wait_for_state(hass, light_group_id, STATE_OFF)

    # Turn on light control
    hass.states.async_set(light_control_switch_id, STATE_ON)
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: light_control_switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, light_control_switch_id, STATE_ON)

    # 1. Area occupied -> Light ON
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        create_area_state_change_event(
            new_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.OCCUPIED],
        ),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, light_group_id, STATE_ON)

    # 2. Area clear -> Light OFF
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        create_area_state_change_event(
            new_states=[AreaStates.CLEAR],
            lost_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.CLEAR],
        ),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, light_group_id, STATE_OFF)

    # 3. Area Bright (but not occupied) -> Light OFF (should stay off)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        create_area_state_change_event(
            new_states=[AreaStates.BRIGHT],
            current_states=[AreaStates.BRIGHT, AreaStates.CLEAR],
        ),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, light_group_id, STATE_OFF)

    # 4. Area Occupied + Bright -> Light ON (because Bright is configured state)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        create_area_state_change_event(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[AreaStates.CLEAR],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        ),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, light_group_id, STATE_ON)

    await shutdown_integration(hass, [light_complex_config_entry])
