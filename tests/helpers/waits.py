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
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
    *,
    timeout: float = 2.0,
) -> None:
    """Wait for an entity to reach a specific state, with timeout.

    Asynchronously waits for an entity to transition to an expected state.
    This is useful for testing state changes that happen asynchronously (e.g.,
    after a service call or automation trigger). The function subscribes to
    state-change events and waits up to the provided timeout.

    Args:
        hass: The Home Assistant instance.
        entity_id: The entity ID to monitor (e.g., 'light.kitchen',
            'binary_sensor.occupancy').
        expected_state: The state value to wait for (e.g., 'on', 'off', '25').
        timeout: Maximum seconds to wait. Default: 2 seconds.

    Raises:
        AssertionError: If the entity doesn't reach the expected state within
            the timeout.

    Note:
        The default timeout is 2 seconds. Pass a shorter timeout for negative
        tests or a longer timeout for slow asynchronous flows.

    Example:
        Wait for a light to turn on after calling a service:

        >>> hass.async_create_task(
        ...     hass.services.async_call("light", "turn_on", ...)
        ... )
        >>> await wait_for_state(hass, "light.kitchen", "on")

    """
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
        await asyncio.wait_for(state_reached, timeout=timeout)
    except TimeoutError as err:
        raise AssertionError(
            f"{entity_id} did not reach state {expected_state!r}"
        ) from err
    finally:
        unsub()
    await hass.async_block_till_done()

    # Final check to raise assertion error if still not matching
    state = hass.states.get(entity_id)
    assert_state(state, expected_state)


async def wait_until(
    hass: HomeAssistant,
    predicate: Callable[[], bool],
    *,
    timeout: float = 2.0,
) -> None:
    """Wait until predicate returns True while cooperatively draining HA."""
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        await hass.async_block_till_done()
        remaining = deadline - monotonic()
        if remaining > 0:
            pause_complete = hass.loop.create_future()
            handle = hass.loop.call_at(
                hass.loop.time() + min(0.01, remaining),
                pause_complete.set_result,
                None,
            )
            try:
                await pause_complete
            finally:
                handle.cancel()
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
    except TimeoutError as err:
        raise AssertionError(
            f"{entity_id} did not reach attribute {attribute_key!r}={expected_value!r}"
        ) from err
    finally:
        unsub()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get(attribute_key) == expected_value
