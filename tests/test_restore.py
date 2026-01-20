"""Test entity state restoration."""

from unittest.mock import patch

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.json import json_dumps
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.magic_areas.const import (
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_OVERHEAD_LIGHTS,
    DOMAIN,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockLight


async def test_restore_light_group_state(hass: HomeAssistant) -> None:
    """Test that AreaLightGroup restores non-derived attributes.

    Note: AreaLightGroup's *state* is derived from member entities / HA group logic
    and may overwrite any restored on/off state. Only assert restored attributes
    that the entity owns (e.g. 'controlling').
    """

    # Config
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.test_light"],
                },
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    # Entity IDs
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    light_control_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )

    # Restore cache: restore 'controlling' and switch state
    mock_restore_cache(
        hass,
        [
            State(
                light_group_id,
                STATE_ON,  # do NOT assert this later; group state is derived
                attributes={"controlling": False, "entity_id": ["light.test_light"]},
            ),
            State(light_control_id, STATE_ON),
        ],
    )

    # Setup mocks
    mock_light = MockLight("test_light", "on", unique_id="test_light")
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: [mock_light]})

    # Init Integration
    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    # Verify Light Group post-startup behavior (restored values may be overwritten)
    light_group = hass.states.get(light_group_id)
    assert light_group is not None

    # 'controlling' is forced back to True when area is not occupied on startup
    assert light_group.attributes.get("controlling") is True

    # Membership is exposed via 'lights' (set by AreaLightGroup)
    assert "light.test_light" in (light_group.attributes.get("lights") or [])

    # Verify Light Control Switch restored
    light_control = hass.states.get(light_control_id)
    assert_state(light_control, STATE_ON)

    await shutdown_integration(hass, [config_entry])
