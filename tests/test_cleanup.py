"""Test cleanup of removed entities."""

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_cleanup_removed_features(hass: HomeAssistant) -> None:
    """Test that entities are removed when a feature is disabled."""

    # 1. Setup with Light Groups enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_LIGHT_GROUPS: {},
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    # Verify Light Control Switch exists
    light_control_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )
    assert hass.states.get(light_control_id) is not None

    registry = er.async_get(hass)
    assert registry.async_get(light_control_id) is not None

    # 2. Update config to disable Light Groups
    new_data = data.copy()
    new_data[CONF_ENABLED_FEATURES] = {}  # Empty features

    hass.config_entries.async_update_entry(config_entry, data=new_data)
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    # 3. Verify Light Control Switch is removed
    # The state should be gone
    assert hass.states.get(light_control_id) is None

    # The entity registry entry should be gone (cleanup_removed_entries calls async_remove)
    # Note: async_remove removes it from the registry
    assert registry.async_get(light_control_id) is None

    await shutdown_integration(hass, [config_entry])
