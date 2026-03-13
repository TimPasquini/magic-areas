"""Config variant tests for Wasp-in-a-Box behavior."""

from types import SimpleNamespace
from typing import Protocol
from unittest.mock import patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.binary_sensor.wasp_in_a_box import ATTR_BOX
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_attribute,
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
    wait_for_state,
    wait_until,
)
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.wasp_in_a_box_testkit",)


class _ScheduledCallback(Protocol):
    """Protocol for loop call_later callback values."""

    def __call__(self, *args: object) -> object: ...


async def test_wasp_timeout_disabled(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
) -> None:
    """Wasp timeout=0 keeps wasp in box (no forget timer)."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.WASP_IN_A_BOX: {
                    CONF_WASP_IN_A_BOX_DELAY: 0,
                    CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 0,
                },
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1},
            },
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)
    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    motion_sensor = entities_wasp_in_a_box[0]

    motion_sensor.turn_on()
    await hass.async_block_till_done()
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_ON)

    motion_sensor.turn_off()
    await hass.async_block_till_done()
    assert_state(hass.states.get(wasp_in_a_box_entity_id), STATE_ON)

    await shutdown_integration(hass, [config_entry])


async def test_wasp_with_delay(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
) -> None:
    """Delay keeps box attr stable until delayed callback executes."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.WASP_IN_A_BOX: {
                    CONF_WASP_IN_A_BOX_DELAY: 1,
                    CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 0,
                },
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1},
            },
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)
    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id

    scheduled_delay: float | None = None
    scheduled_callback: _ScheduledCallback | None = None
    scheduled_args: tuple[object, ...] = ()

    def _capture_call_later(
        delay: float, callback: _ScheduledCallback, *args: object
    ) -> SimpleNamespace:
        nonlocal scheduled_delay, scheduled_callback, scheduled_args
        scheduled_delay = delay
        scheduled_callback = callback
        scheduled_args = args
        return SimpleNamespace(cancel=lambda: None)

    with patch.object(hass.loop, "call_later", side_effect=_capture_call_later):
        hass.states.async_set(door_sensor_entity_id, STATE_ON)
        await wait_until(hass, lambda: scheduled_callback is not None, timeout=2.0)
        state_before = hass.states.get(wasp_in_a_box_entity_id)
        assert_attribute(state_before, ATTR_BOX, STATE_OFF)
        assert scheduled_delay == 1
        assert scheduled_callback is not None
        scheduled_callback(*scheduled_args)
        await hass.async_block_till_done()

    state_after = hass.states.get(wasp_in_a_box_entity_id)
    assert_attribute(state_after, ATTR_BOX, STATE_ON)
    await shutdown_integration(hass, [config_entry])
