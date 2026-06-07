"""Home Assistant websocket, state, and service helpers for simulation."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress

from scripts.ha_dev_bootstrap import HomeAssistantWs
from scripts.ha_dev_simulation.models import TraceState
from scripts.ha_dev_token import DEV_HA_LONG_LIVED_TOKEN


async def get_states(
    client: HomeAssistantWs,
    entity_ids: Iterable[str],
) -> dict[str, TraceState | None]:
    """Return selected HA states keyed by entity id."""
    wanted = set(entity_ids)
    raw_states = await client.call("get_states")
    state_records = raw_states if isinstance(raw_states, list) else []
    states = {
        item["entity_id"]: TraceState(
            state=str(item.get("state")),
            states_attribute=_format_states_attribute(item.get("attributes", {})),
        )
        for item in state_records
        if isinstance(item, Mapping)
        and isinstance(item.get("entity_id"), str)
        and item["entity_id"] in wanted
    }
    return {entity_id: states.get(entity_id) for entity_id in wanted}


def _format_states_attribute(attributes: object) -> str | None:
    """Return a compact area-state attribute string when present."""
    if not isinstance(attributes, Mapping):
        return None
    states = attributes.get("states") or attributes.get("active_states")
    if isinstance(states, list):
        return ",".join(str(state) for state in states)
    if isinstance(states, str):
        return states
    return None


async def call_service(
    client: HomeAssistantWs,
    domain: str,
    service: str,
    *,
    entity_id: str | list[str],
    service_data: Mapping[str, object] | None = None,
) -> None:
    """Call a HA service."""
    payload: dict[str, object] = {
        "domain": domain,
        "service": service,
        "target": {"entity_id": entity_id},
    }
    if service_data:
        payload["service_data"] = dict(service_data)
    await client.call("call_service", **payload)


async def set_input_number(
    client: HomeAssistantWs,
    entity_id: str,
    value: float,
) -> None:
    """Set an input_number value."""
    await call_service(
        client,
        "input_number",
        "set_value",
        entity_id=entity_id,
        service_data={"value": round(value, 3)},
    )


async def set_input_boolean(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set an input_boolean state."""
    await call_service(
        client,
        "input_boolean",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def set_input_select(
    client: HomeAssistantWs,
    entity_id: str,
    option: str,
) -> None:
    """Set an input_select option."""
    await call_service(
        client,
        "input_select",
        "select_option",
        entity_id=entity_id,
        service_data={"option": option},
    )


async def set_switch(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set a switch state."""
    await call_service(
        client,
        "switch",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def set_light(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set a light state through HA's light services."""
    await call_service(
        client,
        "light",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def wait_for_state(
    client: HomeAssistantWs,
    entity_id: str,
    expected_state: str,
    *,
    timeout_seconds: float,
    poll_seconds: float = 1.0,
) -> None:
    """Wait until one entity reaches an expected state."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = (await get_states(client, [entity_id])).get(entity_id)
        if state is not None and state.state == expected_state:
            return
        await asyncio.sleep(poll_seconds)
    state = (await get_states(client, [entity_id])).get(entity_id)
    actual = state.state if state is not None else "<missing>"
    msg = f"{entity_id} did not reach {expected_state}; actual={actual}"
    raise RuntimeError(msg)


async def wait_for_service_call_event(
    args: argparse.Namespace,
    *,
    domain: str,
    service: str,
    trigger: Callable[[], object],
    expected_lights: Iterable[str] = (),
    expected_manual_control: bool | None = None,
    timeout_seconds: float = 10.0,
) -> Mapping[str, object]:
    """Run a trigger and wait for a matching HA call_service event."""
    async with HomeAssistantWs(args.url, DEV_HA_LONG_LIVED_TOKEN) as listener:
        await listener.call("subscribe_events", event_type="call_service")
        wait_task = asyncio.create_task(
            _wait_for_matching_service_call_event(
                listener,
                domain=domain,
                service=service,
                expected_lights=tuple(expected_lights),
                expected_manual_control=expected_manual_control,
                timeout_seconds=timeout_seconds,
            )
        )
        try:
            result = trigger()
            if asyncio.iscoroutine(result):
                await result
            return await wait_task
        finally:
            if not wait_task.done():
                wait_task.cancel()
                with suppress(asyncio.CancelledError):
                    await wait_task


async def _wait_for_matching_service_call_event(
    listener: HomeAssistantWs,
    *,
    domain: str,
    service: str,
    expected_lights: tuple[str, ...],
    expected_manual_control: bool | None,
    timeout_seconds: float,
) -> Mapping[str, object]:
    """Wait for one matching call_service event on an existing listener."""
    if listener._ws is None:
        raise RuntimeError("websocket is not connected")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        timeout = max(0.1, deadline - time.monotonic())
        raw = json.loads(await asyncio.wait_for(listener._ws.recv(), timeout=timeout))
        if raw.get("type") != "event":
            continue
        event = raw.get("event")
        if not isinstance(event, Mapping):
            continue
        data = event.get("data")
        if not isinstance(data, Mapping):
            continue
        if data.get("domain") != domain or data.get("service") != service:
            continue
        service_data = data.get("service_data")
        if not isinstance(service_data, Mapping):
            continue
        if expected_manual_control is not None and (
            service_data.get("manual_control") is not expected_manual_control
        ):
            continue
        if expected_lights:
            raw_lights = service_data.get("lights", [])
            lights = set(raw_lights if isinstance(raw_lights, list) else [])
            if not set(expected_lights).issubset(lights):
                continue
        return service_data

    msg = f"Timed out waiting for {domain}.{service} call_service event"
    raise RuntimeError(msg)
