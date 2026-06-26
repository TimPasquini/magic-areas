"""Event/listener edge-case tests for light groups."""

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import ATTR_STATES
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import assert_state
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockLight
from tests.platforms.light_edge_cases_testkit import get_light_group_runtime


async def test_get_active_lights_missing_entity(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Missing member entity should not break group activation."""
    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"

    hass.states.async_remove("light.overhead_2")
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: light_group_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert_state(hass.states.get(light_group_id), STATE_ON)
    assert_state(hass.states.get("light.overhead_1"), STATE_ON)
    assert_state(hass.states.get("light.overhead_2"), STATE_ON)
    await shutdown_integration(hass, [light_edge_cases_config_entry])


async def test_group_state_changed_logic(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Group state-change parser rejects invalid/restored events."""
    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    target_group = get_light_group_runtime(light_edge_cases_config_entry)

    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )

    event = MagicMock()
    event.context = None
    assert not target_group.group_state_changed(event)

    event.context = MagicMock()
    event.context.origin_event = MagicMock(event_type="state_changed", data={})
    assert not target_group.group_state_changed(event)

    event.context.origin_event.data = {
        "old_state": MagicMock(state=STATE_ON, attributes={"restored": True}),
        "new_state": MagicMock(state=STATE_OFF),
    }
    assert not target_group.group_state_changed(event)
    await shutdown_integration(hass, [light_edge_cases_config_entry])


async def test_light_group_listener_setup_idempotent(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Listener setup should not register duplicate callbacks."""
    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    target_group = get_light_group_runtime(light_edge_cases_config_entry)
    assert target_group._listener_registry.count == 3
    await target_group._setup_listeners()
    assert target_group._listener_registry.count == 3
    await shutdown_integration(hass, [light_edge_cases_config_entry])


async def test_listeners_cleaned_up_on_unload(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Listener registry should be empty after integration unload."""
    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    target_group = get_light_group_runtime(light_edge_cases_config_entry)
    assert target_group._listener_registry.count == 3
    await shutdown_integration(hass, [light_edge_cases_config_entry])
    assert target_group._listener_registry.count == 0
