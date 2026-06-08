"""Switch platform tests for presence-hold contracts."""

from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import CONF_PRESENCE_HOLD_TIMEOUT
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.waits import wait_for_state
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)

pytest_plugins = ("tests.platforms.switch_testkit",)


async def test_switch_snapshot_fields_presence_hold(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test switch snapshot fields used by the platform."""
    await init_integration_helper(hass, [presence_hold_config_entry])

    data = presence_hold_config_entry.runtime_data.coordinator.data
    assert data is not None
    assert MagicAreasFeatures.PRESENCE_HOLD in data.enabled_features
    feature_config = data.feature_configs.get(MagicAreasFeatures.PRESENCE_HOLD)
    assert feature_config is not None
    assert feature_config[CONF_PRESENCE_HOLD_TIMEOUT] == 1

    await shutdown_integration(hass, [presence_hold_config_entry])


async def test_presence_hold_switch_timeout(
    hass: HomeAssistant,
    _setup_integration_presence_hold: None,
    patch_async_call_later: None,
) -> None:
    """Test presence hold switch timeout."""
    switch_id = f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_OFF)


async def test_presence_hold_switch_unload_with_timer(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test presence hold switch unload with active timer."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    switch_id = f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_ON)
    await shutdown_integration(hass, [presence_hold_config_entry])


async def test_presence_hold_switch_unload_no_timer(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test presence hold switch unload without active timer."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    switch_id = f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"
    await wait_for_state(hass, switch_id, STATE_OFF)
    await shutdown_integration(hass, [presence_hold_config_entry])
