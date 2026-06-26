"""Integration parity contracts for light-group entity setup."""

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
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
from tests.helpers.entities import setup_mock_entities
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration,
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

    native_light_ids = {
        entity_id
        for entity_id in hass.states.async_entity_ids(LIGHT_DOMAIN)
        if entity_id.startswith(
            f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_"
        )
    }
    expected_light_ids = {
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_all_lights",
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights",
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_task_lights",
    }

    assert native_light_ids == expected_light_ids
    legacy_policy_light_ids = {
        entity_id
        for entity_id in hass.states.async_entity_ids(LIGHT_DOMAIN)
        if entity_id.startswith(
            f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_"
        )
    }
    assert legacy_policy_light_ids == set()

    all_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_all_lights"
    )
    all_group_state = hass.states.get(all_group_id)
    assert all_group_state is not None

    entity_registry = er.async_get(hass)
    for entity_id in expected_light_ids:
        registry_entry = entity_registry.async_get(entity_id)
        assert registry_entry is not None
        assert registry_entry.hidden_by is None

    label_registry = lr.async_get(hass)
    overhead_label = label_registry.async_get_label_by_name("ma:overhead")
    task_label = label_registry.async_get_label_by_name("ma:task")
    sleep_label = label_registry.async_get_label_by_name("ma:sleep")
    accent_label = label_registry.async_get_label_by_name("ma:accent")
    assert overhead_label is not None
    assert task_label is not None
    assert sleep_label is None
    assert accent_label is None
    overhead_entry = entity_registry.async_get("light.overhead_1")
    task_entry = entity_registry.async_get("light.task_1")
    assert overhead_entry is not None
    assert task_entry is not None
    assert overhead_label.label_id in overhead_entry.labels
    assert task_label.label_id in task_entry.labels

    light_control_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )
    assert hass.states.get(light_control_switch_id) is not None

    await shutdown_integration(hass, [config_entry])
