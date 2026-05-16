#!/usr/bin/env python3
"""Bootstrap the Magic Areas Home Assistant dev instance via HA's websocket API."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    import websockets
except ImportError as err:  # pragma: no cover - handled by shell wrapper.
    raise SystemExit(
        "Missing dependency 'websockets'. Run through ./scripts/ha_dev_bootstrap.sh."
    ) from err

DEFAULT_URL = "ws://localhost:8123/api/websocket"
DEFAULT_HTTP_URL = "http://localhost:8123"
DOMAIN = "magic_areas"


@dataclass(frozen=True, slots=True)
class DevArea:
    """One fake room and the registry-backed entities assigned to it."""

    name: str
    aliases: tuple[str, ...]
    entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OptionsStep:
    """One options-flow menu route and submission payload."""

    step_id: str
    user_input: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class DevMagicArea:
    """One Magic Areas config entry to create/configure for dev."""

    name: str
    flow_name: str | None = None
    options_steps: tuple[OptionsStep, ...] = ()


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
        name="Outdoor Test",
        aliases=("outdoor_test",),
        entity_ids=(
            "binary_sensor.outdoor_bright",
            "sensor.outdoor_illuminance",
        ),
    ),
)

DEV_MAGIC_AREAS: tuple[DevMagicArea, ...] = (
    DevMagicArea(
        name="Living Room",
        options_steps=(
            OptionsStep(
                step_id="area_config",
                user_input={
                    "type": "interior",
                    "include_entities": [],
                    "exclude_entities": [],
                    "reload_on_registry_change": True,
                    "ignore_diagnostic_entities": True,
                },
            ),
            OptionsStep(
                step_id="presence_tracking",
                user_input={
                    "presence_device_platforms": ["binary_sensor"],
                    "presence_sensor_device_class": ["motion", "occupancy", "presence"],
                    "keep_only_entities": [],
                    "clear_timeout": 1,
                },
            ),
            OptionsStep(
                step_id="secondary_states",
                user_input={
                    "dark_entity": "binary_sensor.living_room_light",
                    "sleep_entity": "binary_sensor.living_room_sleep",
                    "accent_entity": "binary_sensor.living_room_accent",
                    "sleep_timeout": 1,
                    "extended_time": 5,
                    "extended_timeout": 10,
                },
            ),
            OptionsStep(
                step_id="select_features",
                user_input={"light_groups": True, "presence_hold": True},
            ),
            OptionsStep(
                step_id="feature_conf_light_groups",
                user_input={
                    "brightness_mode": "inhibit",
                    "adaptive_lighting_mode": "ignore",
                    "overhead_lights": ["light.living_room_overhead"],
                    "overhead_lights_states": ["occupied"],
                    "overhead_lights_act_on": ["occupancy", "state"],
                    "sleep_lights": ["light.living_room_lamp"],
                    "sleep_lights_states": ["sleep"],
                    "sleep_lights_act_on": ["occupancy", "state"],
                    "accent_lights": ["light.living_room_lamp"],
                    "accent_lights_states": ["accented"],
                    "accent_lights_act_on": ["occupancy", "state"],
                    "task_lights": [],
                    "task_lights_states": [],
                    "task_lights_act_on": ["occupancy", "state"],
                },
            ),
            OptionsStep(
                step_id="feature_conf_presence_hold",
                user_input={"presence_hold_timeout": 0},
            ),
        ),
    ),
    DevMagicArea(
        name="Bathroom",
        options_steps=(
            OptionsStep(
                step_id="area_config",
                user_input={
                    "type": "interior",
                    "include_entities": [],
                    "exclude_entities": [],
                    "reload_on_registry_change": True,
                    "ignore_diagnostic_entities": True,
                },
            ),
            OptionsStep(
                step_id="presence_tracking",
                user_input={
                    "presence_device_platforms": ["binary_sensor"],
                    "presence_sensor_device_class": ["motion", "occupancy", "presence"],
                    "keep_only_entities": [],
                    "clear_timeout": 1,
                },
            ),
            OptionsStep(
                step_id="secondary_states",
                user_input={
                    "dark_entity": "binary_sensor.bathroom_light",
                    "sleep_entity": "binary_sensor.bathroom_sleep",
                    "accent_entity": "",
                    "sleep_timeout": 1,
                    "extended_time": 5,
                    "extended_timeout": 10,
                },
            ),
            OptionsStep(
                step_id="select_features",
                user_input={"light_groups": True, "presence_hold": True},
            ),
            OptionsStep(
                step_id="feature_conf_light_groups",
                user_input={
                    "brightness_mode": "inhibit",
                    "adaptive_lighting_mode": "ignore",
                    "overhead_lights": ["light.bathroom_overhead"],
                    "overhead_lights_states": ["occupied"],
                    "overhead_lights_act_on": ["occupancy", "state"],
                    "sleep_lights": ["light.bathroom_sleep_light"],
                    "sleep_lights_states": ["sleep"],
                    "sleep_lights_act_on": ["occupancy", "state"],
                    "accent_lights": [],
                    "accent_lights_states": [],
                    "accent_lights_act_on": ["occupancy", "state"],
                    "task_lights": [],
                    "task_lights_states": [],
                    "task_lights_act_on": ["occupancy", "state"],
                },
            ),
            OptionsStep(
                step_id="feature_conf_presence_hold",
                user_input={"presence_hold_timeout": 0},
            ),
        ),
    ),
    DevMagicArea(name="Interior", flow_name="(Meta) Interior"),
    DevMagicArea(name="Exterior", flow_name="(Meta) Exterior"),
    DevMagicArea(name="Global", flow_name="(Meta) Global"),
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


class HomeAssistantRest:
    """Small Home Assistant REST client for config/options flows."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def post(self, path: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        """POST JSON to the Home Assistant API."""
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
        except HTTPError as err:
            detail = err.read().decode(errors="replace")
            raise RuntimeError(f"POST {path} failed: {err.code} {detail}") from err
        if not body:
            return {}
        result = json.loads(body)
        if not isinstance(result, Mapping):
            raise RuntimeError(f"POST {path} returned non-object JSON: {result}")
        return result


async def wait_for_ha(url: str, token: str, timeout_seconds: int) -> None:
    """Wait until Home Assistant accepts websocket auth."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        try:
            async with HomeAssistantWs(url, token):
                return
        except Exception as err:  # noqa: BLE001 - retry loop reports final failure.
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError(
                    f"Home Assistant did not become ready: {err}"
                ) from err
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


def _entity_lookup(
    entities: list[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
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


def _entry_title(entry: Mapping[str, object]) -> str | None:
    """Return a config entry title when present."""
    title = entry.get("title")
    return title if isinstance(title, str) else None


async def magic_area_entries(
    client: HomeAssistantWs,
) -> list[Mapping[str, object]]:
    """Return Magic Areas config entries from Home Assistant."""
    entries = await client.call("config_entries/get", domain=DOMAIN)
    if not isinstance(entries, list):
        raise RuntimeError(f"Unexpected config_entries/get result: {entries}")
    return [entry for entry in entries if isinstance(entry, Mapping)]


def _find_entry_by_title(
    entries: list[Mapping[str, object]], title: str
) -> Mapping[str, object] | None:
    """Find a config entry by title."""
    normalized = title.lower()
    return next(
        (
            entry
            for entry in entries
            if (_entry_title(entry) or "").lower() == normalized
        ),
        None,
    )


def _flow_id(result: Mapping[str, object]) -> str:
    """Return a flow id from a flow response."""
    flow_id = result.get("flow_id")
    if not isinstance(flow_id, str):
        raise RuntimeError(f"Flow response did not include flow_id: {result}")
    return flow_id


def _entry_id(entry: Mapping[str, object]) -> str:
    """Return a config entry id."""
    entry_id = entry.get("entry_id")
    if not isinstance(entry_id, str):
        raise RuntimeError(f"Config entry did not include entry_id: {entry}")
    return entry_id


def _entry_state(entry: Mapping[str, object]) -> str | None:
    """Return a config entry state."""
    state = entry.get("state")
    return state if isinstance(state, str) else None


async def wait_magic_area_loaded(
    client: HomeAssistantWs,
    title: str,
    *,
    timeout_seconds: int = 30,
) -> None:
    """Wait for a Magic Areas config entry to load before opening options."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        entry = _find_entry_by_title(await magic_area_entries(client), title)
        if entry is not None and _entry_state(entry) == "loaded":
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"Magic Area did not load: {title} ({entry})")
        await asyncio.sleep(0.5)


async def ensure_magic_area_entry(
    client: HomeAssistantWs,
    rest: HomeAssistantRest,
    dev_magic_area: DevMagicArea,
) -> tuple[str, bool]:
    """Create a Magic Areas config entry if missing."""
    existing = _find_entry_by_title(
        await magic_area_entries(client), dev_magic_area.name
    )
    if existing is not None:
        entry_id = _entry_id(existing)
        print(f"magic area already exists: {dev_magic_area.name} ({entry_id})")
        return entry_id, False

    init_result = rest.post(
        "/api/config/config_entries/flow",
        {"handler": DOMAIN, "show_advanced_options": False},
    )
    if init_result.get("type") != "form":
        raise RuntimeError(f"Unexpected config-flow init result: {init_result}")

    create_result = rest.post(
        f"/api/config/config_entries/flow/{_flow_id(init_result)}",
        {"name": dev_magic_area.flow_name or dev_magic_area.name},
    )
    if create_result.get("type") != "create_entry":
        raise RuntimeError(
            f"Unexpected Magic Areas create result for {dev_magic_area.name}: "
            f"{create_result}"
        )

    for _attempt in range(20):
        created = _find_entry_by_title(
            await magic_area_entries(client), dev_magic_area.name
        )
        if created is not None:
            entry_id = _entry_id(created)
            print(f"created magic area: {dev_magic_area.name} ({entry_id})")
            await wait_magic_area_loaded(client, dev_magic_area.name)
            return entry_id, True
        await asyncio.sleep(0.5)

    raise RuntimeError(f"Created Magic Area did not appear: {dev_magic_area.name}")


def _post_options_flow(
    rest: HomeAssistantRest, flow_id: str, user_input: Mapping[str, object]
) -> Mapping[str, object]:
    """Submit one options-flow step."""
    return rest.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        dict(user_input),
    )


async def configure_magic_area_options(
    client: HomeAssistantWs,
    rest: HomeAssistantRest,
    dev_magic_area: DevMagicArea,
    entry_id: str,
    *,
    created: bool,
    force: bool,
) -> None:
    """Apply deterministic dev options to a Magic Areas config entry."""
    if not dev_magic_area.options_steps:
        return
    if not created and not force:
        print(f"magic area options left unchanged: {dev_magic_area.name}")
        return

    await wait_magic_area_loaded(client, dev_magic_area.name)

    result = rest.post(
        "/api/config/config_entries/options/flow",
        {"handler": entry_id, "show_advanced_options": False},
    )
    if result.get("type") != "menu":
        raise RuntimeError(
            f"Unexpected options-flow init result for {dev_magic_area.name}: {result}"
        )

    flow_id = _flow_id(result)
    for options_step in dev_magic_area.options_steps:
        result = _post_options_flow(
            rest, flow_id, {"next_step_id": options_step.step_id}
        )
        if result.get("type") != "form":
            raise RuntimeError(
                f"Unexpected options route result for {dev_magic_area.name}/"
                f"{options_step.step_id}: {result}"
            )
        result = _post_options_flow(rest, flow_id, options_step.user_input)
        if result.get("type") not in {"menu", "create_entry"}:
            raise RuntimeError(
                f"Unexpected options submit result for {dev_magic_area.name}/"
                f"{options_step.step_id}: {result}"
            )
        if result.get("type") == "create_entry":
            raise RuntimeError(
                f"Options flow finished before final step for {dev_magic_area.name}"
            )

    result = _post_options_flow(rest, flow_id, {"next_step_id": "finish"})
    if result.get("type") != "create_entry":
        raise RuntimeError(
            f"Unexpected options finish result for {dev_magic_area.name}: {result}"
        )
    print(f"configured magic area options: {dev_magic_area.name}")


async def ensure_magic_areas(
    client: HomeAssistantWs,
    rest: HomeAssistantRest,
    *,
    force_options: bool,
) -> None:
    """Create/configure the dev Magic Areas entries."""
    for dev_magic_area in DEV_MAGIC_AREAS:
        entry_id, created = await ensure_magic_area_entry(client, rest, dev_magic_area)
        await configure_magic_area_options(
            client,
            rest,
            dev_magic_area,
            entry_id,
            created=created,
            force=force_options,
        )


async def bootstrap(args: argparse.Namespace) -> None:
    """Run bootstrap operations."""
    token = resolve_token(args)
    if not token:
        raise SystemExit(
            "Set HA_TOKEN, pass --token, pass --token-file, or use --token-stdin."
        )

    await wait_for_ha(args.url, token, args.wait)
    rest = HomeAssistantRest(args.http_url, token)
    async with HomeAssistantWs(args.url, token) as client:
        for dev_area in DEV_AREAS:
            area_id = await ensure_area(client, dev_area)
            await assign_entities(
                client,
                area_id=area_id,
                entity_ids=dev_area.entity_ids,
            )
        if not args.skip_magic_areas:
            await ensure_magic_areas(
                client,
                rest,
                force_options=args.force_magic_area_options,
            )
        if not args.skip_initial_states:
            await apply_initial_states(client)

    print("Home Assistant dev bootstrap complete")


def resolve_token(args: argparse.Namespace) -> str:
    """Resolve a Home Assistant token without requiring process-arg exposure."""
    if args.token_stdin:
        return sys.stdin.read().strip()
    if args.token_file:
        return Path(args.token_file).read_text(encoding="utf-8").strip()
    return str(args.token or os.environ.get("HA_TOKEN") or "").strip()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="HA websocket URL")
    parser.add_argument("--http-url", default=DEFAULT_HTTP_URL, help="HA HTTP URL")
    parser.add_argument("--token", help="HA long-lived access token")
    parser.add_argument(
        "--token-file",
        help="Read HA long-lived access token from a local file",
    )
    parser.add_argument(
        "--token-stdin",
        action="store_true",
        help="Read HA long-lived access token from stdin",
    )
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
    parser.add_argument(
        "--skip-magic-areas",
        action="store_true",
        help=(
            "Only create HA areas/entity assignments; "
            "do not create Magic Areas entries"
        ),
    )
    parser.add_argument(
        "--force-magic-area-options",
        action="store_true",
        help="Overwrite existing dev Magic Areas options through options flows",
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
