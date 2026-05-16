#!/usr/bin/env python3
"""Bootstrap the Magic Areas Home Assistant dev instance via HA's websocket API."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
import sys
from typing import Any

try:
    import websockets
except ImportError as err:  # pragma: no cover - handled by shell wrapper.
    raise SystemExit(
        "Missing dependency 'websockets'. Run through ./scripts/ha_dev_bootstrap.sh."
    ) from err

DEFAULT_URL = "ws://localhost:8123/api/websocket"


@dataclass(frozen=True, slots=True)
class DevArea:
    """One fake room and the registry-backed entities assigned to it."""

    name: str
    aliases: tuple[str, ...]
    entity_ids: tuple[str, ...]


DEV_AREAS: tuple[DevArea, ...] = (
    DevArea(
        name="Living Room",
        aliases=("living_room", "Living room"),
        entity_ids=(
            "binary_sensor.living_room_occupancy",
            "binary_sensor.living_room_sleep",
            "binary_sensor.living_room_accent",
            "binary_sensor.living_room_light",
            "sensor.living_room_illuminance",
            "light.living_room_overhead",
            "light.living_room_lamp",
        ),
    ),
    DevArea(
        name="Bathroom",
        aliases=("bathroom",),
        entity_ids=(
            "binary_sensor.bathroom_occupancy",
            "binary_sensor.bathroom_sleep",
            "binary_sensor.bathroom_light",
            "sensor.bathroom_illuminance",
            "light.bathroom_overhead",
            "light.bathroom_sleep_light",
        ),
    ),
    DevArea(
        name="Outside",
        aliases=("outside",),
        entity_ids=(
            "binary_sensor.outdoor_bright",
            "sensor.outdoor_illuminance",
        ),
    ),
)

INITIAL_SERVICE_CALLS: tuple[dict[str, Any], ...] = (
    {
        "domain": "input_boolean",
        "service": "turn_off",
        "target": {
            "entity_id": [
                "input_boolean.living_room_occupancy",
                "input_boolean.living_room_sleep",
                "input_boolean.living_room_accent",
                "input_boolean.living_room_overhead_power",
                "input_boolean.living_room_lamp_power",
                "input_boolean.bathroom_occupancy",
                "input_boolean.bathroom_sleep",
                "input_boolean.bathroom_overhead_power",
                "input_boolean.bathroom_sleep_light_power",
            ]
        },
    },
    {
        "domain": "input_number",
        "service": "set_value",
        "target": {"entity_id": "input_number.living_room_lux"},
        "service_data": {"value": 350},
    },
    {
        "domain": "input_number",
        "service": "set_value",
        "target": {"entity_id": "input_number.bathroom_lux"},
        "service_data": {"value": 120},
    },
    {
        "domain": "input_number",
        "service": "set_value",
        "target": {"entity_id": "input_number.outdoor_lux"},
        "service_data": {"value": 12000},
    },
)


class HomeAssistantWs:
    """Tiny Home Assistant websocket client."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self._next_id = 1
        self._ws: Any = None

    async def __aenter__(self) -> HomeAssistantWs:
        self._ws = await websockets.connect(self.url)
        auth_required = json.loads(await self._ws.recv())
        if auth_required.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected websocket greeting: {auth_required}")
        await self._ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        auth_result = json.loads(await self._ws.recv())
        if auth_result.get("type") != "auth_ok":
            raise RuntimeError(f"Home Assistant authentication failed: {auth_result}")
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._ws is not None:
            await self._ws.close()

    async def call(self, msg_type: str, **payload: object) -> Any:
        """Send one websocket command and return its result."""
        if self._ws is None:
            raise RuntimeError("websocket is not connected")
        msg_id = self._next_id
        self._next_id += 1
        await self._ws.send(json.dumps({"id": msg_id, "type": msg_type, **payload}))
        while True:
            raw = json.loads(await self._ws.recv())
            if raw.get("id") != msg_id:
                continue
            if not raw.get("success", False):
                raise RuntimeError(f"{msg_type} failed: {raw.get('error', raw)}")
            return raw.get("result")


async def wait_for_ha(url: str, token: str, timeout_seconds: int) -> None:
    """Wait until Home Assistant accepts websocket auth."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        try:
            async with HomeAssistantWs(url, token):
                return
        except Exception as err:  # noqa: BLE001 - retry loop reports final failure.
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError(f"Home Assistant did not become ready: {err}") from err
            await asyncio.sleep(2)


def _area_lookup(areas: list[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    """Return area lookup by normalized name and id."""
    lookup: dict[str, Mapping[str, object]] = {}
    for area in areas:
        area_id = area.get("area_id")
        name = area.get("name")
        if isinstance(area_id, str):
            lookup[area_id.lower()] = area
        if isinstance(name, str):
            lookup[name.lower()] = area
    return lookup


def _entity_lookup(entities: list[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    """Return entity registry lookup by entity id."""
    return {
        entity_id: entity
        for entity in entities
        if isinstance(entity_id := entity.get("entity_id"), str)
    }


async def ensure_area(client: HomeAssistantWs, dev_area: DevArea) -> str:
    """Create a dev area if missing and return its area_id."""
    areas = await client.call("config/area_registry/list")
    lookup = _area_lookup(areas)
    for key in (dev_area.name, *dev_area.aliases):
        existing = lookup.get(key.lower())
        if existing and isinstance(existing.get("area_id"), str):
            return str(existing["area_id"])

    created = await client.call("config/area_registry/create", name=dev_area.name)
    area_id = created.get("area_id") if isinstance(created, Mapping) else None
    if not isinstance(area_id, str):
        raise RuntimeError(f"Area creation did not return area_id: {created}")
    print(f"created area: {dev_area.name} ({area_id})")
    return area_id


async def assign_entities(
    client: HomeAssistantWs,
    *,
    area_id: str,
    entity_ids: tuple[str, ...],
) -> None:
    """Assign registry-backed entities to an area."""
    entities = await client.call("config/entity_registry/list")
    lookup = _entity_lookup(entities)
    for entity_id in entity_ids:
        registry_entry = lookup.get(entity_id)
        if registry_entry is None:
            print(f"missing registry entity, skipped: {entity_id}")
            continue
        if registry_entry.get("area_id") == area_id:
            print(f"area already set: {entity_id} -> {area_id}")
            continue
        await client.call(
            "config/entity_registry/update",
            entity_id=entity_id,
            area_id=area_id,
        )
        print(f"assigned entity: {entity_id} -> {area_id}")


async def apply_initial_states(client: HomeAssistantWs) -> None:
    """Set deterministic fake-house defaults through real HA services."""
    for call in INITIAL_SERVICE_CALLS:
        await client.call("call_service", **call)
    print("applied fake-house initial states")


async def bootstrap(args: argparse.Namespace) -> None:
    """Run bootstrap operations."""
    token = args.token or os.environ.get("HA_TOKEN")
    if not token:
        raise SystemExit(
            "Set HA_TOKEN to a Home Assistant long-lived access token, or pass --token."
        )

    await wait_for_ha(args.url, token, args.wait)
    async with HomeAssistantWs(args.url, token) as client:
        for dev_area in DEV_AREAS:
            area_id = await ensure_area(client, dev_area)
            await assign_entities(
                client,
                area_id=area_id,
                entity_ids=dev_area.entity_ids,
            )
        if not args.skip_initial_states:
            await apply_initial_states(client)

    print("Home Assistant dev bootstrap complete")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="HA websocket URL")
    parser.add_argument("--token", help="HA long-lived access token")
    parser.add_argument(
        "--wait",
        type=int,
        default=120,
        help="Seconds to wait for HA websocket readiness",
    )
    parser.add_argument(
        "--skip-initial-states",
        action="store_true",
        help="Only create/assign registries; do not reset fake entity states",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    try:
        asyncio.run(bootstrap(parse_args()))
    except KeyboardInterrupt:
        return 130
    except Exception as err:  # noqa: BLE001 - CLI should print actionable failures.
        print(f"bootstrap failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
