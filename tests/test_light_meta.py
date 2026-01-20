"""Test for meta area light groups."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_ID,
    DOMAIN,
)
from tests.const import DEFAULT_MOCK_AREA, MockAreaIds
from tests.helpers import (
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockLight


@pytest.fixture(name="all_areas_with_meta_config_entry")
async def mock_config_entry_all_areas_with_light_groups() -> list[MockConfigEntry]:
    """Fixture for mock configuration entry."""

    config_entries: list[MockConfigEntry] = []
    for area_entry in MockAreaIds:
        data = get_basic_config_entry_data(area_entry)
        data.update(
            {
                CONF_ENABLED_FEATURES: {
                    CONF_FEATURE_AGGREGATION: {
                        CONF_AGGREGATES_MIN_ENTITIES: 1,
                        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 10,
                    },
                    CONF_FEATURE_LIGHT_GROUPS: {},
                }
            }
        )
        # Set unique_id to match the area ID
        area_id = data.get(CONF_ID, area_entry.value)
        config_entries.append(
            MockConfigEntry(domain=DOMAIN, data=data, unique_id=area_id)
        )

    return config_entries


async def test_meta_light_group(
    hass: HomeAssistant,
    entities_light_one: list[MockLight],
    init_integration_all_areas,
) -> None:
    """Test meta area light group."""
    
    # entities_light_one creates a light in KITCHEN (DEFAULT_MOCK_AREA)
    # KITCHEN is part of INTERIOR, which is part of GLOBAL
    
    global_light_group_id = f"{LIGHT_DOMAIN}.magic_areas_light_groups_global_all_lights"
    
    # Initial state
    await wait_for_state(hass, global_light_group_id, STATE_OFF)
    
    # Turn on the light in Kitchen
    entities_light_one[0].turn_on()
    await hass.async_block_till_done()
    
    # Global light group should turn on
    await wait_for_state(hass, global_light_group_id, STATE_ON)