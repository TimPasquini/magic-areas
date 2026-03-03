"""Integration parity contracts for light-group entity setup."""

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    CONF_TASK_LIGHTS,
    CONF_TASK_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS_STATES,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockLight


async def test_light_group_entity_ids_and_count_match_contract(
    hass: HomeAssistant,
) -> None:
    """Light group platform should create the expected contract entity set."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1"],
                    CONF_OVERHEAD_LIGHTS_STATES: [AreaStates.OCCUPIED],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE],
                    CONF_TASK_LIGHTS: ["light.task_1"],
                    CONF_TASK_LIGHTS_STATES: [AreaStates.OCCUPIED],
                    CONF_TASK_LIGHTS_ACT_ON: [LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE],
                },
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    lights = [
        MockLight("overhead_1", "off", unique_id="overhead_1"),
        MockLight("task_1", "off", unique_id="task_1"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    await init_integration(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    magic_light_ids = {
        entity_id
        for entity_id in hass.states.async_entity_ids(LIGHT_DOMAIN)
        if entity_id.startswith(f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_")
    }
    expected_light_ids = {
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_all_lights",
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights",
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_task_lights",
    }

    assert magic_light_ids == expected_light_ids

    light_control_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )
    assert hass.states.get(light_control_switch_id) is not None

    await shutdown_integration(hass, [config_entry])
