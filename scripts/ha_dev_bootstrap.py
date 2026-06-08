#!/usr/bin/env python3
"""Bootstrap the Magic Areas Home Assistant dev instance via HA's websocket API."""
# ruff: noqa: D102,D105,D107,T201,TRY004

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    import websockets  # type: ignore[import-not-found]
except ImportError as err:  # pragma: no cover - handled by shell wrapper.
    raise SystemExit(
        "Missing dependency 'websockets'. Run through ./scripts/ha_dev_bootstrap.sh."
    ) from err

from scripts.ha_dev_token import DEV_HA_LONG_LIVED_TOKEN

DEFAULT_URL = "ws://localhost:8123/api/websocket"
DEFAULT_HTTP_URL = "http://localhost:8123"
DOMAIN = "magic_areas"


class _WebSocketClient(Protocol):
    """Small websocket protocol surface used by the bootstrap client."""

    async def recv(self) -> str:
        """Receive a websocket message."""
        ...

    async def send(self, message: str) -> None:
        """Send a websocket message."""
        ...

    async def close(self) -> None:
        """Close the websocket connection."""
        ...


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


@dataclass(frozen=True, slots=True)
class DevRoom:
    """One room in the fake-house control matrix."""

    name: str
    slug: str
    brightness_mode: str = "inhibit"
    dark_entity: str | None = None
    adaptive_lighting_mode: str = "ignore"
    adaptive_lighting_manage_all: bool = False
    adaptive_lighting_managed_roles: tuple[str, ...] = ()
    outside_context_source: str = "sun"
    outside_bright_entity: str | None = None
    outside_lux_min: int = 0
    outside_lux_inside_delta: int = 0
    outside_lux_inside_ratio_min_percent: int = 0
    adaptive_require_ambient_rise: bool = False
    ambient_rise_window_seconds: int = 120
    ambient_rise_min_delta: int = 20
    bright_min_on_seconds: int = 0
    bright_dwell_seconds: int = 0
    bright_attribution_hold_seconds: int = 0
    initial_lux: int = 350
    second_light_slug: str = "lamp"
    second_light_label: str = "lamp"
    include_accent: bool = True

    @property
    def occupancy_entity(self) -> str:
        return f"binary_sensor.{self.slug}_occupancy"

    @property
    def sleep_entity(self) -> str:
        return f"binary_sensor.{self.slug}_sleep"

    @property
    def accent_entity(self) -> str:
        return f"binary_sensor.{self.slug}_accent" if self.include_accent else ""

    @property
    def light_entity(self) -> str:
        return f"binary_sensor.{self.slug}_light"

    @property
    def illuminance_entity(self) -> str:
        return f"sensor.{self.slug}_illuminance"

    @property
    def overhead_light(self) -> str:
        return f"light.{self.slug}_overhead"

    @property
    def second_light(self) -> str:
        return f"light.{self.slug}_{self.second_light_slug}"

    @property
    def resolved_dark_entity(self) -> str:
        return self.dark_entity or self.light_entity


DEV_ROOMS: tuple[DevRoom, ...] = (
    DevRoom(name="Living Room", slug="living_room"),
    DevRoom(
        name="Bathroom",
        slug="bathroom",
        initial_lux=120,
        second_light_slug="sleep_light",
        second_light_label="sleep_light",
        include_accent=False,
    ),
    DevRoom(
        name="Classic Sun Room",
        slug="classic_sun_room",
        dark_entity="binary_sensor.outdoor_bright",
    ),
    DevRoom(name="Classic Sensor Room", slug="classic_sensor_room"),
    DevRoom(
        name="Advisory Sun Room",
        slug="advisory_sun_room",
        brightness_mode="advisory",
        dark_entity="binary_sensor.outdoor_bright",
    ),
    DevRoom(
        name="Advisory Sensor Room",
        slug="advisory_sensor_room",
        brightness_mode="advisory",
    ),
    DevRoom(
        name="Startup Unknown Room",
        slug="startup_unknown_room",
        brightness_mode="advisory",
    ),
    DevRoom(
        name="Startup Unavailable Room",
        slug="startup_unavailable_room",
        brightness_mode="advisory",
    ),
    DevRoom(
        name="Adaptive Sun Room",
        slug="adaptive_sun_room",
        brightness_mode="adaptive",
        outside_bright_entity="binary_sensor.outdoor_bright",
        bright_min_on_seconds=2,
        bright_dwell_seconds=2,
        bright_attribution_hold_seconds=2,
    ),
    DevRoom(
        name="Adaptive Binary Room",
        slug="adaptive_binary_room",
        brightness_mode="adaptive",
        outside_bright_entity="binary_sensor.outdoor_bright",
        bright_min_on_seconds=2,
        bright_dwell_seconds=2,
        bright_attribution_hold_seconds=2,
    ),
    DevRoom(
        name="Adaptive Lux Room",
        slug="adaptive_lux_room",
        brightness_mode="adaptive",
        outside_context_source="outside_lux",
        outside_lux_min=1000,
        outside_lux_inside_delta=500,
        outside_lux_inside_ratio_min_percent=150,
        bright_min_on_seconds=2,
        bright_dwell_seconds=2,
        bright_attribution_hold_seconds=2,
    ),
    DevRoom(
        name="Adaptive Ambient Room",
        slug="adaptive_ambient_room",
        brightness_mode="adaptive",
        outside_bright_entity="binary_sensor.outdoor_bright",
        adaptive_require_ambient_rise=True,
        ambient_rise_window_seconds=60,
        ambient_rise_min_delta=100,
        bright_min_on_seconds=2,
        bright_dwell_seconds=2,
        bright_attribution_hold_seconds=2,
    ),
    DevRoom(
        name="Adaptive Manual Light Room",
        slug="adaptive_manual_light_room",
        brightness_mode="adaptive",
        outside_bright_entity="binary_sensor.outdoor_bright",
        adaptive_require_ambient_rise=True,
        ambient_rise_window_seconds=60,
        ambient_rise_min_delta=100,
        bright_min_on_seconds=2,
        bright_dwell_seconds=2,
        bright_attribution_hold_seconds=2,
    ),
    DevRoom(
        name="Adaptive Lighting Room",
        slug="adaptive_lighting_room",
        brightness_mode="advisory",
        adaptive_lighting_mode="manage",
        adaptive_lighting_manage_all=True,
        adaptive_lighting_managed_roles=("overhead_lights", "sleep_lights"),
    ),
)


def _room_dev_area(room: DevRoom) -> DevArea:
    """Build the HA area/entity assignment for one fake room."""
    return DevArea(
        name=room.name,
        aliases=(room.slug,),
        entity_ids=(
            room.occupancy_entity,
            room.sleep_entity,
            room.light_entity,
            room.illuminance_entity,
            room.overhead_light,
            room.second_light,
            *(() if not room.include_accent else (room.accent_entity,)),
        ),
    )


def _light_group_mode_options(room: DevRoom) -> dict[str, object]:
    """Return light-group brightness behavior options for one dev room."""
    return {"brightness_mode": room.brightness_mode}


def _light_group_brightness_detail_options(room: DevRoom) -> dict[str, object]:
    """Return advisory/adaptive brightness detail options for one dev room."""
    options: dict[str, object] = {}
    if room.brightness_mode in {"advisory", "adaptive"}:
        options["inside_bright_entity"] = room.light_entity
        if room.outside_bright_entity:
            options["outside_bright_entity"] = room.outside_bright_entity
    if room.brightness_mode == "adaptive":
        options.update(
            {
                "bright_min_on_seconds": room.bright_min_on_seconds,
                "bright_dwell_seconds": room.bright_dwell_seconds,
                "outside_context_source": room.outside_context_source,
                "outside_lux_entity": "sensor.outdoor_illuminance",
                "outside_lux_min": room.outside_lux_min,
                "outside_lux_inside_entity": room.illuminance_entity,
                "outside_lux_inside_delta": room.outside_lux_inside_delta,
                "outside_lux_inside_ratio_min_percent": (
                    room.outside_lux_inside_ratio_min_percent
                ),
                "bright_attribution_hold_seconds": (
                    room.bright_attribution_hold_seconds
                ),
                "adaptive_require_ambient_rise": room.adaptive_require_ambient_rise,
                "ambient_rise_window_seconds": room.ambient_rise_window_seconds,
                "ambient_rise_min_delta": room.ambient_rise_min_delta,
            }
        )
    return options


def _light_group_brightness_options_steps(room: DevRoom) -> tuple[OptionsStep, ...]:
    """Return brightness options-flow steps for one dev room."""
    steps = [
        OptionsStep(
            step_id="feature_conf_light_groups_brightness",
            user_input=_light_group_mode_options(room),
        )
    ]
    if room.brightness_mode in {"advisory", "adaptive"}:
        steps.append(
            OptionsStep(
                step_id=(
                    "feature_conf_light_groups_brightness_advisory"
                    if room.brightness_mode == "advisory"
                    else "feature_conf_light_groups_brightness_adaptive"
                ),
                user_input=_light_group_brightness_detail_options(room),
            )
        )
    return tuple(steps)


def _light_group_adaptive_lighting_options(room: DevRoom) -> dict[str, object]:
    """Return Adaptive Lighting coordination options for one dev room."""
    options: dict[str, object] = {
        "adaptive_lighting_mode": room.adaptive_lighting_mode,
    }
    if room.adaptive_lighting_mode == "manage":
        options.update(
            {
                "adaptive_lighting_manage_all_lights": room.adaptive_lighting_manage_all,
                "adaptive_lighting_managed_roles": list(
                    room.adaptive_lighting_managed_roles
                ),
            }
        )
    return options


def _light_group_options(room: DevRoom) -> dict[str, object]:
    """Return light-role membership options for one dev room."""
    return {
        "overhead_lights": [room.overhead_light],
        "overhead_lights_states": ["occupied"],
        "overhead_lights_act_on": ["occupancy", "state"],
        "sleep_lights": [room.second_light],
        "sleep_lights_states": ["sleep"],
        "sleep_lights_act_on": ["occupancy", "state"],
        "accent_lights": [room.second_light] if room.include_accent else [],
        "accent_lights_states": ["accented"] if room.include_accent else [],
        "accent_lights_act_on": ["occupancy", "state"],
        "task_lights": [],
        "task_lights_states": [],
        "task_lights_act_on": ["occupancy", "state"],
    }


def _room_magic_area(room: DevRoom) -> DevMagicArea:
    """Build the Magic Areas config/options flow plan for one fake room."""
    return DevMagicArea(
        name=room.name,
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
                    "dark_entity": room.resolved_dark_entity,
                    "sleep_entity": room.sleep_entity,
                    "accent_entity": room.accent_entity,
                    "sleep_timeout": 1,
                    "extended_time": 1,
                    "extended_timeout": 1,
                },
            ),
            OptionsStep(
                step_id="select_features",
                user_input={"light_groups": True, "presence_hold": True},
            ),
            *_light_group_brightness_options_steps(room),
            OptionsStep(
                step_id="feature_conf_light_groups_adaptive_lighting",
                user_input=_light_group_adaptive_lighting_options(room),
            ),
            OptionsStep(
                step_id="feature_conf_light_groups_roles",
                user_input=_light_group_options(room),
            ),
            OptionsStep(
                step_id="feature_conf_presence_hold",
                user_input={"presence_hold_timeout": 0},
            ),
        ),
    )


def _fan_room_magic_area() -> DevMagicArea:
    """Build the Magic Areas config/options flow plan for fan validation."""
    return DevMagicArea(
        name="Fan Room",
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
                    "dark_entity": "binary_sensor.fan_room_light",
                    "sleep_entity": "binary_sensor.fan_room_sleep",
                    "accent_entity": "binary_sensor.fan_room_accent",
                    "sleep_timeout": 1,
                    "extended_time": 1,
                    "extended_timeout": 1,
                },
            ),
            OptionsStep(
                step_id="select_features",
                user_input={"fan_groups": True, "presence_hold": True},
            ),
            OptionsStep(
                step_id="feature_conf_fan_groups_humidity",
                user_input={
                    "members": ["fan.fan_room_exhaust"],
                    "sensor_entity_id": "sensor.fan_room_humidity",
                    "detection_mode": "threshold_trend",
                    "on_threshold": 60.0,
                    "hysteresis": 5.0,
                    "active_states": ["occupied", "extended"],
                    "suppress_states": ["sleep"],
                    "clear_behavior": "post_clear_hold",
                    "post_clear_hold_seconds": 4,
                    "sensor_unavailable_behavior": "hold_then_clear",
                },
            ),
            OptionsStep(
                step_id="feature_conf_fan_groups_odor",
                user_input={
                    "members": ["fan.fan_room_exhaust"],
                    "sensor_entity_id": "sensor.fan_room_voc",
                    "detection_mode": "threshold",
                    "on_threshold": 500.0,
                    "hysteresis": 100.0,
                    "active_states": ["occupied", "extended"],
                    "suppress_states": [],
                    "clear_behavior": "run_until_clear",
                    "post_clear_hold_seconds": 0,
                    "sensor_unavailable_behavior": "hold_until_restored",
                },
            ),
            OptionsStep(
                step_id="feature_conf_presence_hold",
                user_input={"presence_hold_timeout": 0},
            ),
        ),
    )


def _cover_room_magic_area() -> DevMagicArea:
    """Build the Magic Areas config/options flow plan for cover validation."""
    return DevMagicArea(
        name="Cover Room",
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
                    "dark_entity": "binary_sensor.cover_room_light",
                    "sleep_entity": "binary_sensor.cover_room_sleep",
                    "accent_entity": "binary_sensor.cover_room_accent",
                    "sleep_timeout": 1,
                    "extended_time": 1,
                    "extended_timeout": 1,
                },
            ),
            OptionsStep(
                step_id="select_features",
                user_input={"cover_groups": True, "presence_hold": True},
            ),
            OptionsStep(
                step_id="feature_conf_cover_groups_settings",
                user_input={
                    "automation_device_classes": [
                        "blind",
                        "curtain",
                        "shade",
                        "shutter",
                        "window",
                    ],
                    "manual_hold_seconds": 2,
                    "daylight_action": "open",
                    "daylight_states": ["occupied", "extended"],
                    "privacy_action": "close",
                    "privacy_states": ["sleep"],
                    "accent_action": "close",
                    "accent_states": ["accented"],
                },
            ),
            OptionsStep(
                step_id="feature_conf_presence_hold",
                user_input={"presence_hold_timeout": 0},
            ),
        ),
    )


DEV_AREAS: tuple[DevArea, ...] = (
    *(_room_dev_area(room) for room in DEV_ROOMS),
    DevArea(
        name="Fan Room",
        aliases=("fan_room",),
        entity_ids=(
            "binary_sensor.fan_room_occupancy",
            "binary_sensor.fan_room_sleep",
            "binary_sensor.fan_room_accent",
            "binary_sensor.fan_room_light",
            "sensor.fan_room_illuminance",
            "sensor.fan_room_humidity",
            "sensor.fan_room_voc",
            "input_select.fan_room_humidity_availability",
            "input_select.fan_room_voc_availability",
            "fan.fan_room_exhaust",
        ),
    ),
    DevArea(
        name="Cover Room",
        aliases=("cover_room",),
        entity_ids=(
            "binary_sensor.cover_room_occupancy",
            "binary_sensor.cover_room_sleep",
            "binary_sensor.cover_room_accent",
            "binary_sensor.cover_room_light",
            "sensor.cover_room_illuminance",
            "cover.cover_room_blinds",
            "cover.cover_room_shades",
            "cover.cover_room_curtains",
            "cover.cover_room_shutters",
            "cover.cover_room_window",
            "cover.cover_room_garage",
            "cover.cover_room_door",
        ),
    ),
    DevArea(
        name="Setup Room",
        aliases=("setup_room",),
        entity_ids=(
            "binary_sensor.setup_room_occupancy",
            "binary_sensor.setup_room_motion",
            "binary_sensor.setup_room_sleep",
            "binary_sensor.setup_room_accent",
            "binary_sensor.setup_room_light",
            "binary_sensor.setup_room_door",
            "binary_sensor.setup_room_window",
            "binary_sensor.setup_room_problem",
            "binary_sensor.setup_room_smoke",
            "sensor.setup_room_illuminance",
            "sensor.setup_room_temperature",
            "sensor.setup_room_humidity",
            "sensor.setup_room_ble_source",
            "light.setup_room_overhead",
            "light.setup_room_task",
            "light.setup_room_accent",
            "light.setup_room_sleep_light",
            "fan.setup_room_fan",
            "cover.setup_room_blinds",
            "media_player.setup_room_speaker",
            "climate.setup_room_thermostat",
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
    *(_room_magic_area(room) for room in DEV_ROOMS),
    _fan_room_magic_area(),
    _cover_room_magic_area(),
    DevMagicArea(name="Interior", flow_name="(Meta) Interior"),
    DevMagicArea(name="Exterior", flow_name="(Meta) Exterior"),
    DevMagicArea(name="Global", flow_name="(Meta) Global"),
)


def _initial_boolean_entities() -> list[str]:
    """Return fake input booleans that should reset to off."""
    entities: list[str] = []
    for room in DEV_ROOMS:
        entities.extend(
            [
                f"input_boolean.{room.slug}_occupancy",
                f"input_boolean.{room.slug}_sleep",
                f"input_boolean.{room.slug}_accent",
                f"input_boolean.{room.slug}_overhead_power",
                (
                    f"input_boolean.{room.slug}_sleep_light_power"
                    if room.second_light_slug == "sleep_light"
                    else f"input_boolean.{room.slug}_lamp_power"
                ),
            ]
        )
    entities.extend(
        [
            "input_boolean.setup_room_occupancy",
            "input_boolean.setup_room_motion",
            "input_boolean.setup_room_sleep",
            "input_boolean.setup_room_accent",
            "input_boolean.setup_room_door",
            "input_boolean.setup_room_window",
            "input_boolean.setup_room_problem",
            "input_boolean.setup_room_smoke",
            "input_boolean.setup_room_overhead_power",
            "input_boolean.setup_room_task_power",
            "input_boolean.setup_room_accent_power",
            "input_boolean.setup_room_sleep_light_power",
            "input_boolean.setup_room_fan_power",
            "input_boolean.setup_room_blinds_open",
            "input_boolean.setup_room_heater",
            "input_boolean.setup_room_speaker_power",
            "input_boolean.fan_room_occupancy",
            "input_boolean.fan_room_sleep",
            "input_boolean.fan_room_accent",
            "input_boolean.fan_room_exhaust_power",
            "input_boolean.cover_room_occupancy",
            "input_boolean.cover_room_sleep",
            "input_boolean.cover_room_accent",
            "input_boolean.cover_room_blinds_open",
            "input_boolean.cover_room_shades_open",
            "input_boolean.cover_room_curtains_open",
            "input_boolean.cover_room_shutters_open",
            "input_boolean.cover_room_window_open",
            "input_boolean.cover_room_garage_open",
            "input_boolean.cover_room_door_open",
        ]
    )
    return entities


def _initial_service_calls() -> tuple[dict[str, object], ...]:
    """Return deterministic fake-house reset service calls."""
    calls: list[dict[str, object]] = [
        {
            "domain": "input_boolean",
            "service": "turn_off",
            "target": {"entity_id": _initial_boolean_entities()},
        }
    ]
    calls.extend(
        {
            "domain": "input_number",
            "service": "set_value",
            "target": {"entity_id": f"input_number.{room.slug}_lux"},
            "service_data": {"value": room.initial_lux},
        }
        for room in DEV_ROOMS
    )
    calls.extend(
        [
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.setup_room_lux"},
                "service_data": {"value": 350},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.setup_room_temperature"},
                "service_data": {"value": 72},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.setup_room_humidity"},
                "service_data": {"value": 45},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.fan_room_lux"},
                "service_data": {"value": 350},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.fan_room_humidity"},
                "service_data": {"value": 45},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.fan_room_voc"},
                "service_data": {"value": 0},
            },
            {
                "domain": "input_select",
                "service": "select_option",
                "target": {"entity_id": "input_select.fan_room_humidity_availability"},
                "service_data": {"option": "available"},
            },
            {
                "domain": "input_select",
                "service": "select_option",
                "target": {"entity_id": "input_select.fan_room_voc_availability"},
                "service_data": {"option": "available"},
            },
            {
                "domain": "input_number",
                "service": "set_value",
                "target": {"entity_id": "input_number.cover_room_lux"},
                "service_data": {"value": 350},
            },
        ]
    )
    calls.append(
        {
            "domain": "input_number",
            "service": "set_value",
            "target": {"entity_id": "input_number.outdoor_lux"},
            "service_data": {"value": 12000},
        }
    )
    calls.append(
        {
            "domain": "input_select",
            "service": "select_option",
            "target": {
                "entity_id": "input_select.startup_unknown_room_light_availability"
            },
            "service_data": {"option": "available"},
        }
    )
    calls.append(
        {
            "domain": "input_select",
            "service": "select_option",
            "target": {
                "entity_id": "input_select.startup_unavailable_room_light_availability"
            },
            "service_data": {"option": "available"},
        }
    )
    return tuple(calls)


INITIAL_SERVICE_CALLS: tuple[dict[str, object], ...] = _initial_service_calls()



class HomeAssistantWs:
    """Tiny Home Assistant websocket client."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self._next_id = 1
        self._call_lock = asyncio.Lock()
        self._ws: _WebSocketClient | None = None

    async def __aenter__(self) -> HomeAssistantWs:
        self._ws = cast(
            _WebSocketClient,
            await websockets.connect(self.url, open_timeout=10),
        )
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

    async def call(self, msg_type: str, **payload: object) -> object:
        """Send one websocket command and return its result."""
        if self._ws is None:
            raise RuntimeError("websocket is not connected")
        async with self._call_lock:
            msg_id = self._next_id
            self._next_id += 1
            await self._ws.send(
                json.dumps({"id": msg_id, "type": msg_type, **payload})
            )
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
            raise RuntimeError(
                f"POST {path} failed: {err.code} payload={payload} {detail}"
            ) from err
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


def _mapping_list(value: object) -> list[Mapping[str, object]]:
    """Return list items that are mapping-shaped API records."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


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
    lookup = _area_lookup(_mapping_list(areas))
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
    lookup = _entity_lookup(_mapping_list(entities))
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


def _route_options_step(
    rest: HomeAssistantRest,
    flow_id: str,
    step_id: str,
    current_result: Mapping[str, object],
) -> Mapping[str, object]:
    """Route from the options root menu to a concrete form step."""
    current_step_id = current_result.get("step_id")
    if current_result.get("type") == "form" and current_step_id == step_id:
        return current_result
    if step_id.startswith("feature_conf_light_groups_"):
        if current_step_id != "feature_conf_light_groups":
            result = _post_options_flow(
                rest, flow_id, {"next_step_id": "feature_conf_light_groups"}
            )
            if result.get("type") != "menu":
                return result
    elif current_step_id == "feature_conf_light_groups":
        result = _post_options_flow(rest, flow_id, {"next_step_id": "show_menu"})
        if result.get("type") != "menu":
            return result
    if step_id.startswith("feature_conf_fan_groups_"):
        if current_step_id != "feature_conf_fan_groups":
            result = _post_options_flow(
                rest, flow_id, {"next_step_id": "feature_conf_fan_groups"}
            )
            if result.get("type") != "menu":
                return result
    elif current_step_id == "feature_conf_fan_groups":
        result = _post_options_flow(rest, flow_id, {"next_step_id": "show_menu"})
        if result.get("type") != "menu":
            return result
    if step_id.startswith("feature_conf_cover_groups_"):
        if current_step_id != "feature_conf_cover_groups":
            result = _post_options_flow(
                rest, flow_id, {"next_step_id": "feature_conf_cover_groups"}
            )
            if result.get("type") != "menu":
                return result
    elif current_step_id == "feature_conf_cover_groups":
        result = _post_options_flow(rest, flow_id, {"next_step_id": "show_menu"})
        if result.get("type") != "menu":
            return result
    return _post_options_flow(rest, flow_id, {"next_step_id": step_id})


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
    for index, options_step in enumerate(dev_magic_area.options_steps):
        result = _route_options_step(rest, flow_id, options_step.step_id, result)
        if result.get("type") != "form":
            raise RuntimeError(
                f"Unexpected options route result for {dev_magic_area.name}/"
                f"{options_step.step_id}: {result}"
            )
        result = _post_options_flow(rest, flow_id, options_step.user_input)
        if result.get("type") == "form":
            next_step = (
                dev_magic_area.options_steps[index + 1]
                if index + 1 < len(dev_magic_area.options_steps)
                else None
            )
            if next_step is not None and result.get("step_id") == next_step.step_id:
                continue
        if result.get("type") not in {"menu", "create_entry"}:
            raise RuntimeError(
                f"Unexpected options submit result for {dev_magic_area.name}/"
                f"{options_step.step_id}: {result}"
            )
        if result.get("type") == "create_entry":
            raise RuntimeError(
                f"Options flow finished before final step for {dev_magic_area.name}"
            )

    menu_options = result.get("menu_options")
    if not isinstance(menu_options, list) or "finish" in menu_options:
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
    only_magic_area: str | None,
) -> None:
    """Create/configure the dev Magic Areas entries."""
    for dev_magic_area in DEV_MAGIC_AREAS:
        if only_magic_area is not None and dev_magic_area.name != only_magic_area:
            continue
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
    await wait_for_ha(args.url, DEV_HA_LONG_LIVED_TOKEN, args.wait)
    rest = HomeAssistantRest(args.http_url, DEV_HA_LONG_LIVED_TOKEN)
    async with HomeAssistantWs(args.url, DEV_HA_LONG_LIVED_TOKEN) as client:
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
                only_magic_area=args.only_magic_area,
            )
        if not args.skip_initial_states:
            await apply_initial_states(client)

    print("Home Assistant dev bootstrap complete")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="HA websocket URL")
    parser.add_argument("--http-url", default=DEFAULT_HTTP_URL, help="HA HTTP URL")
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
    parser.add_argument(
        "--only-magic-area",
        help="Only create/configure the named Magic Areas config entry.",
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
