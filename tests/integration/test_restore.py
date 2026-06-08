"""Test entity state restoration."""


from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import assert_state
from tests.helpers.entities import setup_mock_entities
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import shutdown_integration
from tests.helpers.lifecycle import init_integration as init_integration_helper
from tests.mocks import MockLight


async def test_restore_light_group_state(hass: HomeAssistant) -> None:
    """Native helper light groups remain restored while MA policy is non-entity."""

    # Config
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.test_light"],
                },
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    # Entity IDs
    native_light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_"
        f"{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    legacy_policy_light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    light_control_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )

    # Restore cache: stale legacy policy state should not recreate an entity.
    mock_restore_cache(
        hass,
        [
            State(
                legacy_policy_light_group_id,
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

    assert hass.states.get(legacy_policy_light_group_id) is None

    native_light_group = hass.states.get(native_light_group_id)
    assert native_light_group is not None
    assert "light.test_light" in (native_light_group.attributes.get("entity_id") or [])

    # Verify Light Control Switch restored
    light_control = hass.states.get(light_control_id)
    assert_state(light_control, STATE_ON)

    await shutdown_integration(hass, [config_entry])
