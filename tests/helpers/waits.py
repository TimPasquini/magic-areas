"""Asynchronous wait helpers shared across Magic Areas tests."""

import asyncio
from collections.abc import Callable
from time import monotonic

from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event

from tests.helpers.assertions import assert_state


async def wait_for_state(
    hass: HomeAssistant, entity_id: str, expected_state: str
) -> None:
    """Wait for an entity to reach a specific state."""
    state = hass.states.get(entity_id)
    if state and state.state == expected_state:
        return

    state_reached = asyncio.get_running_loop().create_future()

    @callback
    def _on_state_change(event: Event[EventStateChangedData]) -> None:
        new_state = event.data.get("new_state")
        if not new_state or new_state.state != expected_state:
            return
        if not state_reached.done():
            state_reached.set_result(None)

    unsub = async_track_state_change_event(hass, [entity_id], _on_state_change)
    state = hass.states.get(entity_id)
    if state and state.state == expected_state and not state_reached.done():
        state_reached.set_result(None)
    try:
        await asyncio.wait_for(state_reached, timeout=2.0)
    finally:
        unsub()
    await hass.async_block_till_done()

    assert_state(hass.states.get(entity_id), expected_state)


async def wait_until(
    hass: HomeAssistant,
    predicate: Callable[[], bool],
    *,
    timeout: float = 2.0,
) -> None:
    """Wait until a predicate succeeds while draining the Home Assistant loop."""
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        await hass.async_block_till_done()
    raise AssertionError("Timed out waiting for expected condition")


async def wait_for_attribute(
    hass: HomeAssistant,
    entity_id: str,
    attribute_key: str,
    expected_value: object,
    *,
    timeout: float = 2.0,
) -> None:
    """Wait for an entity attribute to reach an expected value."""
    state = hass.states.get(entity_id)
    if state and state.attributes.get(attribute_key) == expected_value:
        return

    attribute_reached = asyncio.get_running_loop().create_future()

    @callback
    def _on_state_change(event: Event[EventStateChangedData]) -> None:
        new_state = event.data.get("new_state")
        if not new_state:
            return
        if new_state.attributes.get(attribute_key) != expected_value:
            return
        if not attribute_reached.done():
            attribute_reached.set_result(None)

    unsub = async_track_state_change_event(hass, [entity_id], _on_state_change)
    state = hass.states.get(entity_id)
    if (
        state
        and state.attributes.get(attribute_key) == expected_value
        and not attribute_reached.done()
    ):
        attribute_reached.set_result(None)
    try:
        await asyncio.wait_for(attribute_reached, timeout=timeout)
    finally:
        unsub()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get(attribute_key) == expected_value
