"""Test for meta area light groups."""

import pytest
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_ID,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import MockAreaIds
from tests.helpers.waits import wait_for_state
from tests.helpers.config_entries import get_basic_config_entry_data
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
                    MagicAreasFeatures.AGGREGATES: {
                        CONF_AGGREGATES_MIN_ENTITIES: 1,
                        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 10,
                    },
                    MagicAreasFeatures.LIGHT_GROUPS: {},
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
    init_integration_all_areas: list[MockConfigEntry],
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
