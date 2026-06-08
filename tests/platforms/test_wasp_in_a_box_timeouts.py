"""Timeout behavior tests for Wasp-in-a-Box."""

import inspect
from collections.abc import Callable
from unittest.mock import patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    ATTR_BOX,
    ATTR_WASP,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import (
    assert_attribute,
    assert_state,
)
from tests.helpers.waits import wait_for_attribute
from tests.helpers import drain_hass
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.wasp_in_a_box_testkit",)


async def test_wasp_timeout_triggers_forget(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box: None,
    patch_async_call_later: None,
) -> None:
    """When wasp sensor goes off in a closed box, timeout forgets the wasp."""
    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    hass.states.async_set(door_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    wiab_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wiab_state, STATE_ON)
    assert_attribute(wiab_state, ATTR_WASP, STATE_ON)
    assert_attribute(wiab_state, ATTR_BOX, STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    final = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(final, STATE_OFF)
    assert_attribute(final, ATTR_WASP, STATE_OFF)
    assert_attribute(final, ATTR_BOX, STATE_OFF)


async def test_open_box_cancels_timer(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box: None,
) -> None:
    """Opening the box cancels an in-flight forget timer."""
    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    hass.states.async_set(door_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    wiab_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wiab_state, STATE_ON)
    assert_attribute(wiab_state, ATTR_WASP, STATE_ON)
    assert_attribute(wiab_state, ATTR_BOX, STATE_OFF)

    fired_callback: Callable[[object], object] | None = None

    def capture_callback(_hass_obj: object, _delay: object, callback: object) -> Callable[[], None]:
        nonlocal fired_callback
        if callable(callback):
            fired_callback = callback
        return lambda: None

    with patch(
        "custom_components.magic_areas.helpers.async_call_later",
        side_effect=capture_callback,
    ):
        hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
        await hass.async_block_till_done()

    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await wait_for_attribute(hass, wasp_in_a_box_entity_id, ATTR_BOX, STATE_ON)
    final = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(final, STATE_OFF)
    assert_attribute(final, ATTR_BOX, STATE_ON)

    if fired_callback is not None:
        callback_result = fired_callback(None)
        if inspect.isawaitable(callback_result):
            await callback_result
            await drain_hass(hass)
        final_after = hass.states.get(wasp_in_a_box_entity_id)
        assert_state(final_after, STATE_OFF)
        assert_attribute(final_after, ATTR_BOX, STATE_ON)


async def test_wasp_seen_cancels_timer(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box: None,
    patch_async_call_later: None,
) -> None:
    """Seeing motion again cancels a scheduled forget timer."""
    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    hass.states.async_set(door_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    wiab_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wiab_state, STATE_ON)
    assert_attribute(wiab_state, ATTR_WASP, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    final = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(final, STATE_ON)
    assert_attribute(final, ATTR_WASP, STATE_ON)
